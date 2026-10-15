#!/usr/bin/env bash
set -e
export LD_LIBRARY_PATH=/opt/oracle/instantclient_23_4:${LD_LIBRARY_PATH:-}
exec python3 app.py
