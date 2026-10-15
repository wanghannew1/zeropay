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
