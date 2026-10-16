"""Generate schema_cn.py from Oracle data dictionary (CCRCPQ.TC93 / CCRCPQ.TC8M).

Connects via the project's db module, queries ALL_TAB_COLUMNS and ALL_COL_COMMENTS,
and writes schema_cn.py with TC93_FIELDS, TC8M_KEY_FIELDS, and EXPORT_COLUMNS.

Run: python3 gen_schema_cn.py
"""

import os
import sys

# Ensure project root is on sys.path so we can import db
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db


# Head 8 columns in exact order (output_key, field_name, chinese_comment)
HEAD_8 = [
    ("AAC003", "AAC003", "姓名"),
    ("AAC002", "AAC002", "公民身份号码"),
    ("AAC001", "AAC001", "个人编号"),
    ("AAE00B", "AAE00B", "员工号"),
    ("ATB930", "ATB930", "结算单元流水号"),
    ("ATB931", "ATB931", "结算单元名称"),
    ("ATC931", "ATC931", "工资所属年月"),
    ("ATC937", "ATC937", "工资发放次数"),
]

# TC8M aggregated export columns (output_key, header, kind)
TC8M_KEY_FIELDS = [
    ("STATUS_LABEL", "发放状态", "str"),
    ("ATC8M3_MIN", "工资状态最小值(ATC8M3_MIN)", "str"),
    ("ATC8M3_MAX", "工资状态最大值(ATC8M3_MAX)", "str"),
    ("ATC8G7", "经办年月(ATC8G7)", "int"),
    ("BBB002_LIST", "发放银行汇总(BBB002)", "str"),
    ("ATB90AB_MAX", "工资发放日(ATB90AB)", "int"),
    ("ATC8M2_SUM", "发放总额合计(ATC8M2)", "money"),
    ("ATC8M1_MAX", "发放人数(ATC8M1)", "int"),
]

# Explicit kind overrides (field_name -> kind)
KIND_OVERRIDES = {
    "ATC8M1": "int",  # 发放人数 is a count, not money
    "ATB90AB": "int",  # 工资发放日 is day-of-month NUMBER(2)
}


def derive_kind(data_type, data_precision, data_scale, field_name):
    """Derive kind from Oracle data dictionary metadata.

    Rules:
    - DATE -> date
    - VARCHAR2/CHAR -> str
    - NUMBER with scale >= 2 -> money
    - NUMBER with scale = 0 and precision >= 16 -> id (16-digit identifiers)
    - NUMBER with scale = 0 and precision < 16 -> int (includes YYYYMM months)
    - Explicit overrides applied after the rule
    """
    # Check explicit overrides first
    if field_name in KIND_OVERRIDES:
        return KIND_OVERRIDES[field_name]

    if data_type == "DATE":
        return "date"
    elif data_type in ("VARCHAR2", "CHAR"):
        return "str"
    elif data_type == "NUMBER":
        if data_scale is not None and data_scale >= 2:
            return "money"
        elif data_scale == 0:
            if data_precision is not None and data_precision >= 16:
                return "id"
            else:
                return "int"
        else:
            # Default for NUMBER without clear scale/precision
            return "str"
    else:
        # Fallback
        return "str"


def fetch_table_columns(conn, owner, table_name):
    """Fetch columns for a table from ALL_TAB_COLUMNS with comments from ALL_COL_COMMENTS.

    Returns list of dicts: {field_name, comment, data_type, data_precision, data_scale, column_id}
    Ordered by column_id.
    """
    cursor = conn.cursor()
    try:
        query = """
            SELECT c.COLUMN_NAME, c.DATA_TYPE, c.DATA_PRECISION, c.DATA_SCALE, c.COLUMN_ID,
                   cc.COMMENTS
              FROM ALL_TAB_COLUMNS c
              LEFT JOIN ALL_COL_COMMENTS cc
                ON cc.OWNER = c.OWNER
               AND cc.TABLE_NAME = c.TABLE_NAME
               AND cc.COLUMN_NAME = c.COLUMN_NAME
             WHERE c.OWNER = :owner
               AND c.TABLE_NAME = :table_name
             ORDER BY c.COLUMN_ID
        """
        cursor.execute(query, {"owner": owner, "table_name": table_name})
        columns = []
        for row in cursor.fetchall():
            col_name, data_type, data_precision, data_scale, column_id, comment = row
            columns.append({
                "field_name": col_name,
                "comment": comment if comment else col_name,
                "data_type": data_type,
                "data_precision": data_precision,
                "data_scale": data_scale,
                "column_id": column_id,
            })
        return columns
    finally:
        cursor.close()


def generate_schema_cn():
    """Generate schema_cn.py from Oracle data dictionary."""
    print("Initializing database connection...")
    db.init_db()
    conn = db.get_connection()

    try:
        print("Fetching TC93 columns...")
        tc93_columns = fetch_table_columns(conn, "CCRCPQ", "TC93")
        print(f"  Found {len(tc93_columns)} TC93 columns")

        print("Fetching TC8M columns...")
        tc8m_columns = fetch_table_columns(conn, "CCRCPQ", "TC8M")
        print(f"  Found {len(tc8m_columns)} TC8M columns")

        # Build TC93_FIELDS list (all 180 in column_id order)
        tc93_fields = []
        for col in tc93_columns:
            kind = derive_kind(
                col["data_type"],
                col["data_precision"],
                col["data_scale"],
                col["field_name"],
            )
            tc93_fields.append({
                "field": col["field_name"],
                "comment": col["comment"],
                "kind": kind,
            })

        # Build EXPORT_COLUMNS
        # 1. Head 8 columns
        head_8_fields = []
        for output_key, field_name, chinese_comment in HEAD_8:
            # Find the matching TC93 field to get its kind
            tc93_field = next((f for f in tc93_fields if f["field"] == field_name), None)
            if not tc93_field:
                raise ValueError(f"Head column {field_name} not found in TC93")
            head_8_fields.append({
                "field": output_key,
                "header": f"{chinese_comment}({field_name})",
                "kind": tc93_field["kind"],
            })

        # 2. Remaining 172 TC93 fields (skip the 8 already placed)
        head_8_field_names = {field_name for _, field_name, _ in HEAD_8}
        remaining_tc93 = []
        for tc93_field in tc93_fields:
            if tc93_field["field"] not in head_8_field_names:
                remaining_tc93.append({
                    "field": tc93_field["field"],
                    "header": f"{tc93_field['comment']}({tc93_field['field']})",
                    "kind": tc93_field["kind"],
                })

        # 3. TC8M_KEY_FIELDS (8 columns)
        tc8m_export = []
        for output_key, header, kind in TC8M_KEY_FIELDS:
            tc8m_export.append({
                "field": output_key,
                "header": header,
                "kind": kind,
            })

        # Combine
        export_columns = head_8_fields + remaining_tc93 + tc8m_export

        # Assertions
        assert len(tc93_fields) == 180, f"Expected 180 TC93 fields, got {len(tc93_fields)}"
        assert len(tc8m_export) == 8, f"Expected 8 TC8M export columns, got {len(tc8m_export)}"
        assert len(export_columns) == 188, f"Expected 188 export columns, got {len(export_columns)}"

        # Verify head 8 order
        expected_head_8_fields = ["AAC003", "AAC002", "AAC001", "AAE00B", "ATB930", "ATB931", "ATC931", "ATC937"]
        actual_head_8_fields = [col["field"] for col in head_8_fields]
        assert actual_head_8_fields == expected_head_8_fields, f"Head 8 order mismatch: {actual_head_8_fields}"

        print(f"  TC93 fields: {len(tc93_fields)}")
        print(f"  TC8M export columns: {len(tc8m_export)}")
        print(f"  Total export columns: {len(export_columns)}")

        # Write schema_cn.py
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema_cn.py")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write('"""Generated by gen_schema_cn.py from Oracle data dictionary (CCRCPQ.TC93 / CCRCPQ.TC8M).\n')
            f.write('Do not edit by hand; re-run gen_schema_cn.py after schema changes.\n')
            f.write('"""\n\n')

            # TC93_FIELDS
            f.write("# TC93 fields in data dictionary column_id order (180 entries)\n")
            f.write("TC93_FIELDS = [\n")
            for field in tc93_fields:
                f.write(f'    {{"field": {field["field"]!r}, "comment": {field["comment"]!r}, "kind": {field["kind"]!r}}},\n')
            f.write("]\n\n")

            # TC8M_KEY_FIELDS
            f.write("# TC8M aggregated export columns (8 entries)\n")
            f.write("TC8M_KEY_FIELDS = [\n")
            for field in tc8m_export:
                f.write(f'    {{"field": {field["field"]!r}, "header": {field["header"]!r}, "kind": {field["kind"]!r}}},\n')
            f.write("]\n\n")

            # EXPORT_COLUMNS
            f.write("# Final export columns in order (188 entries: 8 head + 172 remaining TC93 + 8 TC8M)\n")
            f.write("EXPORT_COLUMNS = [\n")
            for field in export_columns:
                f.write(f'    {{"field": {field["field"]!r}, "header": {field["header"]!r}, "kind": {field["kind"]!r}}},\n')
            f.write("]\n")

        print(f"Generated {output_path}")
        print("Assertions passed: 180 TC93 / 8 TC8M / 188 export columns")

    finally:
        db.release_connection(conn)
        db.close_db()


if __name__ == "__main__":
    generate_schema_cn()
