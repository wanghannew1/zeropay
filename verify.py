#!/usr/bin/env python3
"""Live verification script for ZeroPay."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import db
from queries import get_salary_by_cert

# 测试用身份证号经环境变量注入，避免入库真实身份信息
CERT = os.environ.get("ZP_TEST_CERT", "")
EXPECTED_ROWS = int(os.environ.get("ZP_TEST_ROWS", "359"))
EXPECTED_BLANK = int(os.environ.get("ZP_TEST_BLANK", "24"))
VALID_STATUSES = {"待确认", "确认可发放", "已发放"}

def main():
    print("=" * 60)
    print("ZeroPay Live Verification")
    print("=" * 60)

    if not CERT:
        print("缺少环境变量 ZP_TEST_CERT（测试用身份证号），已中止")
        return 2

    db.init_db()
    conn = db.get_connection()
    try:
        rows = get_salary_by_cert(conn, CERT)
    finally:
        db.release_connection(conn)
        db.close_db()

    # 1. Row count
    count = len(rows)
    ok1 = count == EXPECTED_ROWS
    print(f"\n[{'PASS' if ok1 else 'FAIL'}] Row count: {count} (expected {EXPECTED_ROWS})")

    # 2. No duplicate ATC930
    atc930_values = [r["ATC930"] for r in rows]
    dupes = len(atc930_values) - len(set(atc930_values))
    ok2 = dupes == 0
    print(f"[{'PASS' if ok2 else 'FAIL'}] Duplicate ATC930: {dupes} (expected 0)")

    # 3. Person info
    name = rows[0]["AAC003"] if rows else None
    aac001 = rows[0]["AAC001"] if rows else None
    exp_name = os.environ.get("ZP_TEST_NAME")
    exp_aac001 = os.environ.get("ZP_TEST_AAC001")
    if exp_name or exp_aac001:
        ok3 = (exp_name is None or name == exp_name) and (
            exp_aac001 is None or str(aac001) == exp_aac001
        )
    else:
        ok3 = True
    print(f"[{'PASS' if ok3 else 'FAIL'}] Person: name={name}, aac001={aac001} (expect env ZP_TEST_NAME/ZP_TEST_AAC001 if set)")

    # 4. Blank status count
    blank_count = sum(1 for r in rows if r["STATUS_LABEL"] == "")
    ok4 = blank_count == EXPECTED_BLANK
    print(f"[{'PASS' if ok4 else 'FAIL'}] Blank status rows: {blank_count} (expected {EXPECTED_BLANK})")

    # 5. All non-blank statuses are valid
    non_blank_statuses = {r["STATUS_LABEL"] for r in rows if r["STATUS_LABEL"] != ""}
    # Valid: exact labels OR "部分发放(X/Y)" pattern
    import re
    invalid = set()
    for s in non_blank_statuses:
        if s in VALID_STATUSES:
            continue
        if re.match(r"^部分发放\(\d+/\d+\)$", s):
            continue
        invalid.add(s)
    ok5 = len(invalid) == 0
    print(f"[{'PASS' if ok5 else 'FAIL'}] Non-blank statuses: {non_blank_statuses}")
    if invalid:
        print(f"       INVALID statuses found: {invalid}")

    # 6. Check that blank rows have None for raw fields
    blank_rows = [r for r in rows if r["STATUS_LABEL"] == ""]
    all_blank_raw_ok = all(
        r["STATUS_RAW_MIN"] is None and r["STATUS_RAW_MAX"] is None and r["JINGBAN_MONTH"] is None
        for r in blank_rows
    )
    ok6 = all_blank_raw_ok
    print(f"[{'PASS' if ok6 else 'FAIL'}] Blank rows have None raw fields: {all_blank_raw_ok}")

    # Summary
    all_pass = all([ok1, ok2, ok3, ok4, ok5, ok6])
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {'ALL PASS ✓' if all_pass else 'SOME FAILED ✗'}")
    print(f"{'=' * 60}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
