SQL = """
SELECT t.*,
       st.ATC8M3_MIN, st.ATC8M3_MAX, st.ATC8G7
  FROM TC93 t
  LEFT JOIN (
      SELECT ATB930, ATC931, ATC937,
             MIN(ATC8M3) AS ATC8M3_MIN,
             MAX(ATC8M3) AS ATC8M3_MAX,
             MAX(ATC8G7) AS ATC8G7
        FROM TC8M
       GROUP BY ATB930, ATC931, ATC937
  ) st ON st.ATB930 = t.ATB930
     AND st.ATC931 = t.ATC931
     AND st.ATC937 = t.ATC937
 WHERE t.AAC002 = :cert
 ORDER BY t.ATC931, t.ATC937, t.ATB930
"""

STATUS_FILTER_SQL = {
    "unpaid": "st.ATC8M3_MIN IS NULL",
    "not_paid": "(st.ATC8M3_MIN IS NULL OR st.ATC8M3_MIN <> '2')",
    "all": None,
}

STATUS_LABELS = {
    "0": "待确认",
    "1": "确认可发放",
    "2": "已发放",
}


def get_salary_by_cert(conn, cert):
    """Query TC93 salary rows for a given cert number, LEFT JOIN TC8M for status.

    Returns list[dict] with all TC93 columns plus ATC8M3_MIN, ATC8M3_MAX, ATC8G7.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(SQL, {"cert": cert})
        columns = [col[0].upper() for col in cursor.description]
        rows = []
        for raw in cursor.fetchall():
            row = dict(zip(columns, raw))
            # Compute display status
            atc8m3_min = row.get("ATC8M3_MIN")
            atc8m3_max = row.get("ATC8M3_MAX")
            atc8g7 = row.get("ATC8G7")

            if atc8m3_min is None:
                # No TC8M match -> blank (未发放)
                status_label = ""
                status_raw_min = None
                status_raw_max = None
                jingban_month = None
            elif atc8m3_min == atc8m3_max:
                status_label = STATUS_LABELS.get(str(atc8m3_min), str(atc8m3_min))
                status_raw_min = str(atc8m3_min)
                status_raw_max = str(atc8m3_max)
                jingban_month = str(atc8g7) if atc8g7 is not None else None
            else:
                status_label = f"部分发放({atc8m3_min}/{atc8m3_max})"
                status_raw_min = str(atc8m3_min)
                status_raw_max = str(atc8m3_max)
                jingban_month = str(atc8g7) if atc8g7 is not None else None

            row["STATUS_LABEL"] = status_label
            row["STATUS_RAW_MIN"] = status_raw_min
            row["STATUS_RAW_MAX"] = status_raw_max
            row["JINGBAN_MONTH"] = jingban_month
            rows.append(row)
        return rows
    finally:
        cursor.close()


def get_cross_unit_salary_rows(conn, month=None, pay_month=None, status="unpaid", scope="cross_unit"):
    """Query TC93 salary rows with TC8M aggregates, for cross-unit or all people.

    Returns (columns, row_iter) where columns is the list of output keys from
    schema_cn.EXPORT_COLUMNS and row_iter is a generator yielding tuples of raw
    DB values of length 188 in EXPORT_COLUMNS order, with STATUS_LABEL computed
    and inserted at index 180.

    month: filter by TC93.ATC931 (工资所属年月), int or None.
    pay_month: filter by aggregated TC8M.ATC8G7 (经办年月), int or None.
        Rows with no TC8M record (NULL ATC8G7) are excluded when set.
    status: one of "unpaid", "not_paid", "all".
    scope: "cross_unit" (default) restricts to employees whose TC93 rows span
        more than one distinct ATB930 (cross-settlement-unit); "all" includes
        every TC93 row. Unknown values raise ValueError.

    The caller must consume the iterator before releasing the connection.
    """
    from schema_cn import EXPORT_COLUMNS

    if status not in STATUS_FILTER_SQL:
        raise ValueError(f"Unknown status: {status}")
    if scope not in ("cross_unit", "all"):
        raise ValueError(f"Unknown scope: {scope}")

    tc93_fields = []
    tc8m_fields = []
    for idx, col in enumerate(EXPORT_COLUMNS):
        if col["field"] == "STATUS_LABEL":
            continue
        if idx < 180:
            tc93_fields.append(col["field"])
        else:
            tc8m_fields.append(col["field"])

    select_cols = ", ".join(f"t.{field}" for field in tc93_fields)
    tc8m_cols = ", ".join(f"st.{field}" for field in tc8m_fields)

    if scope == "cross_unit":
        cte_and_join = """
WITH cross_unit AS (
    SELECT /*+ MATERIALIZE */ AAC002 FROM TC93
     GROUP BY AAC002
    HAVING MIN(ATB930) <> MAX(ATB930)
),
st AS (
    SELECT /*+ MATERIALIZE */ ATB930, ATC931, ATC937,
           MIN(ATC8M3) AS ATC8M3_MIN, MAX(ATC8M3) AS ATC8M3_MAX,
           MAX(ATC8G7) AS ATC8G7, MAX(ATB90AB) AS ATB90AB_MAX,
           SUM(ATC8M2) AS ATC8M2_SUM, MAX(ATC8M1) AS ATC8M1_MAX,
           LISTAGG(BBB002, ',') WITHIN GROUP (ORDER BY BBB002) AS BBB002_LIST
      FROM TC8M
     GROUP BY ATB930, ATC931, ATC937
)
SELECT {select_cols},
       {tc8m_cols}
  FROM TC93 t
  JOIN cross_unit c ON c.AAC002 = t.AAC002
  LEFT JOIN st ON st.ATB930 = t.ATB930 AND st.ATC931 = t.ATC931 AND st.ATC937 = t.ATC937
""".format(select_cols=select_cols, tc8m_cols=tc8m_cols)
    else:  # scope == "all"
        cte_and_join = """
WITH st AS (
    SELECT /*+ MATERIALIZE */ ATB930, ATC931, ATC937,
           MIN(ATC8M3) AS ATC8M3_MIN, MAX(ATC8M3) AS ATC8M3_MAX,
           MAX(ATC8G7) AS ATC8G7, MAX(ATB90AB) AS ATB90AB_MAX,
           SUM(ATC8M2) AS ATC8M2_SUM, MAX(ATC8M1) AS ATC8M1_MAX,
           LISTAGG(BBB002, ',') WITHIN GROUP (ORDER BY BBB002) AS BBB002_LIST
      FROM TC8M
     GROUP BY ATB930, ATC931, ATC937
)
SELECT {select_cols},
       {tc8m_cols}
  FROM TC93 t
  LEFT JOIN st ON st.ATB930 = t.ATB930 AND st.ATC931 = t.ATC931 AND st.ATC937 = t.ATC937
""".format(select_cols=select_cols, tc8m_cols=tc8m_cols)

    sql = cte_and_join + " WHERE 1=1\n"

    params = {}
    if month is not None:
        sql += "   AND t.ATC931 = :month\n"
        params["month"] = month

    if pay_month is not None:
        sql += "   AND st.ATC8G7 = :pay_month\n"
        params["pay_month"] = pay_month

    status_filter = STATUS_FILTER_SQL[status]
    if status_filter:
        sql += f"   AND {status_filter}\n"

    sql += " ORDER BY t.AAC002, t.ATC931, t.ATC937, t.ATB930"

    cursor = conn.cursor()
    cursor.arraysize = 1000

    try:
        cursor.execute(sql, params)
        columns = [col["field"] for col in EXPORT_COLUMNS]

        def row_generator():
            try:
                while True:
                    rows = cursor.fetchmany(1000)
                    if not rows:
                        break
                    for raw in rows:
                        atc8m3_min = raw[180]
                        atc8m3_max = raw[181]

                        if atc8m3_min is None:
                            status_label = ""
                        elif atc8m3_min == atc8m3_max:
                            status_label = STATUS_LABELS.get(str(atc8m3_min), str(atc8m3_min))
                        else:
                            status_label = f"部分发放({atc8m3_min}/{atc8m3_max})"

                        yield raw[:180] + (status_label,) + raw[180:]
            finally:
                cursor.close()

        return columns, row_generator()
    except Exception:
        cursor.close()
        raise
