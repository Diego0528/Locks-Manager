import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = 'lm-saflok-pha-2026-x9k2'
    DB_DRIVER = 'ODBC Driver 17 for SQL Server'
    DB_SERVER = 'localhost'
    DB_NAME = 'LockManager'

    # Battery: 3 AA batteries
    BATTERY_CELLS = 3
    BATTERY_MAX_V = 4.5   # 3 × 1.5V fully charged
    BATTERY_MIN_V = 2.7   # 3 × 0.9V depleted cutoff
    BATTERY_ALERT_PCT = 25  # % below which alert is shown

    # Hotel info for reports
    HOTEL_NAME = 'PHA Hotel'
    REPORT_CODE = 'SIS.PHA.REG.026'
    DEFAULT_MODEL = '790'
    DEFAULT_SUPERVISOR = 'MB'
    BATTERY_STALE_DAYS = 90  # días sin lectura = cerradura desactualizada

    # Usuarios del sistema: usuario → {password, full_name}
    # Agrega o cambia usuarios aquí según el personal
    USERS = {
        'admin':   {'password': 'admin',  'full_name': 'Administrador'},
        'diego': {'password': 'diego',  'full_name': 'Diego Andrino'},
    }
