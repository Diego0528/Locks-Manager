"""
Locks Manager - Configuration Template
Copyright (c) 2026 Diego Andrino. All rights reserved.

Copy this file to config.py and fill in the values for your environment.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    # Generate a strong random key, e.g.: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY = 'change-this-to-a-random-secret-key'

    # SQL Server connection
    DB_DRIVER = 'ODBC Driver 17 for SQL Server'
    DB_SERVER = 'localhost'           # or your server hostname / IP
    DB_NAME = 'LockManager'          # name of the database

    # Battery thresholds (3 AA batteries)
    BATTERY_CELLS = 3
    BATTERY_MAX_V = 4.5              # 3 × 1.5V fully charged
    BATTERY_MIN_V = 2.7              # 3 × 0.9V depleted cutoff
    BATTERY_ALERT_PCT = 25           # % below which alert is shown
    BATTERY_STALE_DAYS = 90          # days without reading = outdated lock

    # Hotel info shown on reports
    HOTEL_NAME = 'Your Hotel Name'
    REPORT_CODE = 'SIS.XXX.REG.000'
    DEFAULT_MODEL = '790'
    DEFAULT_SUPERVISOR = 'XX'

    # System users: username -> {password, full_name}
    # Add or change users here for your staff
    USERS = {
        'admin': {'password': 'change-this-password', 'full_name': 'Administrator'},
        # 'user2': {'password': 'another-password', 'full_name': 'Full Name'},
    }
