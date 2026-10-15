#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLIENT_DIR="$ROOT/instantclient_23_4"
ZIP_PATH="$ROOT/instantclient-basic-linux64-23.4.zip"
ZIP_URL="${ZERO_PAY_CLIENT_ZIP_URL:-https://download.oracle.com/otn_software/linux/instantclient/2340000/instantclient-basic-linux.x64-23.4.0.24.05.zip}"

resolve_client() {
  if [ -n "${ORACLE_CLIENT_LIB_DIR:-}" ] && [ -d "$ORACLE_CLIENT_LIB_DIR" ]; then
    echo "$ORACLE_CLIENT_LIB_DIR"
  elif [ -d "$CLIENT_DIR" ]; then
    echo "$CLIENT_DIR"
  elif [ -d /opt/oracle/instantclient_23_4 ]; then
    echo /opt/oracle/instantclient_23_4
  else
    echo ""
  fi
}

CLIENT="$(resolve_client)"

if [ -z "$CLIENT" ]; then
  if [ ! -f "$ZIP_PATH" ]; then
    echo "[oracle] 下载 Oracle Instant Client Basic (~113MB)，请稍候..."
    echo "[oracle] $ZIP_URL"
    curl -fL -H "Cookie: oraclelicense=accept-securebackup-cookie" -o "$ZIP_PATH" "$ZIP_URL"
  else
    echo "[oracle] 使用本地压缩包: $ZIP_PATH"
  fi
  TMP="$ROOT/.client_extract"
  rm -rf "$TMP" && mkdir -p "$TMP"
  unzip -q "$ZIP_PATH" -d "$TMP"
  SRC="$(dirname "$(find "$TMP" -name 'libclntsh.so*' | head -1)")"
  mv "$SRC" "$CLIENT_DIR"
  rm -rf "$TMP"
  CLIENT="$CLIENT_DIR"
  echo "[oracle] 已解压就绪: $CLIENT"
fi

export ORACLE_CLIENT_LIB_DIR="$CLIENT"
export LD_LIBRARY_PATH="$CLIENT${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec python3 app.py
