import os
import oracledb
from config import DB_CONFIG

ORACLE_CLIENT_LIB_DIR = "/opt/oracle/instantclient_23_4"

_pool = None


def init_db():
    global _pool
    # Set LD_LIBRARY_PATH BEFORE init_oracle_client (required for thick mode)
    os.environ["LD_LIBRARY_PATH"] = (
        ORACLE_CLIENT_LIB_DIR + ":" + os.environ.get("LD_LIBRARY_PATH", "")
    )
    oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB_DIR)
    dsn = f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['service_name']}"
    _pool = oracledb.create_pool(
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        dsn=dsn,
        min=1,
        max=5,
        timeout=300,
        disable_oob=True,
        tcp_connect_timeout=10,
    )
    print(f"Database pool created: {dsn} (min={_pool.min}, max={_pool.max})")


def get_connection():
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _pool.acquire()


def release_connection(conn):
    if _pool is not None and conn is not None:
        _pool.release(conn)


def close_db():
    global _pool
    if _pool:
        _pool.close()
        _pool = None
        print("Database pool closed")
