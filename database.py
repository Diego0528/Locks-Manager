import pyodbc
from config import Config


def get_connection():
    conn_str = (
        f"DRIVER={{{Config.DB_DRIVER}}};"
        f"SERVER={Config.DB_SERVER};"
        f"DATABASE={Config.DB_NAME};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


def _rows_as_dicts(cursor):
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def query(sql, params=None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        return _rows_as_dicts(cur)


def query_one(sql, params=None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        row = cur.fetchone()
        if row is None:
            return None
        cols = [col[0] for col in cur.description]
        return dict(zip(cols, row))


def execute(sql, params=None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()
        return cur.rowcount


def insert(sql, params=None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        cur.execute("SELECT SCOPE_IDENTITY()")
        new_id = cur.fetchone()[0]
        conn.commit()
        return int(new_id) if new_id else None


def calc_battery_pct(voltage):
    voltage = float(voltage)
    pct = (voltage - Config.BATTERY_MIN_V) / (Config.BATTERY_MAX_V - Config.BATTERY_MIN_V) * 100
    return max(0, min(100, round(pct)))


def battery_color(pct):
    if pct >= 75:
        return 'success'
    elif pct >= 50:
        return 'warning-light'
    elif pct >= 25:
        return 'warning'
    return 'danger'
