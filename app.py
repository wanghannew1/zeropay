import io
import re
from decimal import Decimal

from flask import Flask, jsonify, render_template, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, numbers
from openpyxl.utils import get_column_letter

import db
from queries import get_salary_by_cert

app = Flask(__name__)

CERT_RE = re.compile(r"^[0-9]{17}[0-9X]$")

# Money fields to format as 2-decimal floats
MONEY_FIELDS = {
    "ATC93X", "ATC933", "ATC934", "ATC935", "ATC936", "ATC93K",
    "ATC93AA", "ATC93D", "ATC93C", "ATC93AB",
}


def _serialize_row(row):
    """Convert Oracle row dict to JSON-safe dict."""
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif v is None:
            out[k] = None
        else:
            out[k] = v
    return out


def _validate_cert(cert_raw):
    cert = (cert_raw or "").strip().upper()
    if not CERT_RE.match(cert):
        return None, "身份证号格式错误，应为18位（末位可为X）"
    return cert, None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/salary")
def api_salary():
    cert_raw = request.args.get("cert", "")
    cert, err = _validate_cert(cert_raw)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    conn = None
    try:
        conn = db.get_connection()
        rows = get_salary_by_cert(conn, cert)
    except Exception as e:
        return jsonify({"ok": False, "error": f"数据库查询失败: {e}"}), 500
    finally:
        db.release_connection(conn)

    if not rows:
        return jsonify({"ok": True, "cert": cert, "name": None, "count": 0, "rows": []})

    name = rows[0].get("AAC003")
    aac001 = rows[0].get("AAC001")
    serialized = []
    for r in rows:
        s = _serialize_row(r)
        s["status_label"] = r["STATUS_LABEL"]
        s["status_raw_min"] = r["STATUS_RAW_MIN"]
        s["status_raw_max"] = r["STATUS_RAW_MAX"]
        s["jingban_month"] = r["JINGBAN_MONTH"]
        serialized.append(s)

    return jsonify({
        "ok": True,
        "cert": cert,
        "name": name,
        "aac001": aac001,
        "count": len(serialized),
        "rows": serialized,
    })


# Excel export column spec: (header, field_key, is_money)
EXCEL_COLUMNS = [
    ("姓名", "AAC003", False),
    ("身份证号", "AAC002", False),
    ("个人编号", "AAC001", False),
    ("员工号", "AAE00B", False),
    ("结算单元", "ATB931", False),
    ("工资所属年月", "ATC931", False),
    ("发放年月(ATC932)", "ATC932", False),
    ("发放批次", "ATC937", False),
    ("本次基本工资(ATC93X)", "ATC93X", True),
    ("本次应发工资(ATC933)", "ATC933", True),
    ("本次扣款(ATC934)", "ATC934", True),
    ("本次补发(ATC935)", "ATC935", True),
    ("本次免税(ATC936)", "ATC936", True),
    ("本次年终奖(ATC93K)", "ATC93K", True),
    ("本次工资总额(ATC93AA)", "ATC93AA", True),
    ("本次个人所得税(ATC93D)", "ATC93D", True),
    ("本次实发金额(ATC93C)", "ATC93C", True),
    ("累计应税金额(ATC93AB)", "ATC93AB", True),
    ("发放状态", "status_label", False),
    ("状态原值(ATC8M3_MIN)", "status_raw_min", False),
    ("经办年月(ATC8G7)", "jingban_month", False),
]


@app.route("/api/salary/export")
def api_salary_export():
    cert_raw = request.args.get("cert", "")
    cert, err = _validate_cert(cert_raw)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    conn = None
    try:
        conn = db.get_connection()
        rows = get_salary_by_cert(conn, cert)
    except Exception as e:
        return jsonify({"ok": False, "error": f"数据库查询失败: {e}"}), 500
    finally:
        db.release_connection(conn)

    wb = Workbook()
    ws = wb.active
    ws.title = "工资明细"

    # Header row
    bold = Font(bold=True)
    for col_idx, (header, _, _) in enumerate(EXCEL_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = bold

    # Data rows
    for row_idx, r in enumerate(rows, start=2):
        for col_idx, (_, field, is_money) in enumerate(EXCEL_COLUMNS, start=1):
            val = r.get(field)
            if isinstance(val, Decimal):
                val = float(val)
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            if is_money and val is not None:
                cell.number_format = "0.00"

    # Freeze top row
    ws.freeze_panes = "A2"

    # Auto-width (approximate)
    for col_idx, (header, _, _) in enumerate(EXCEL_COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = max(len(header) * 1.8, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"工资明细_{cert}.xlsx",
    )


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5001, debug=False)
