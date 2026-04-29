"""
Run ONCE to create the database and seed initial data.
  python init_db.py
"""
import pyodbc
from config import Config


def get_master_conn():
    conn_str = (
        f"DRIVER={{{Config.DB_DRIVER}}};"
        f"SERVER={Config.DB_SERVER};"
        f"DATABASE=master;"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
        f"autocommit=True;"
    )
    conn = pyodbc.connect(conn_str, autocommit=True)
    return conn


SCHEMA_SQL = """
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'LockManager')
    CREATE DATABASE LockManager;
"""

TABLES_SQL = """
USE LockManager;

IF OBJECT_ID('lock_events', 'U') IS NULL
CREATE TABLE lock_events (
    id          INT PRIMARY KEY IDENTITY(1,1),
    lock_id     INT NOT NULL,
    event_date  DATE NOT NULL,
    event_type  NVARCHAR(60),
    description NVARCHAR(MAX),
    resolved    BIT DEFAULT 0,
    resolved_date DATE,
    created_at  DATETIME2 DEFAULT SYSDATETIME()
);

IF OBJECT_ID('clock_configs', 'U') IS NULL
CREATE TABLE clock_configs (
    id          INT PRIMARY KEY IDENTITY(1,1),
    lock_id     INT NOT NULL,
    config_date DATE NOT NULL,
    technician  NVARCHAR(100),
    notes       NVARCHAR(500),
    created_at  DATETIME2 DEFAULT SYSDATETIME()
);

IF OBJECT_ID('battery_readings', 'U') IS NULL
CREATE TABLE battery_readings (
    id               INT PRIMARY KEY IDENTITY(1,1),
    lock_id          INT NOT NULL,
    reading_date     DATE NOT NULL,
    technician       NVARCHAR(100),
    voltage          DECIMAL(4,2) NOT NULL,
    percentage       TINYINT,
    batteries_changed BIT DEFAULT 0,
    notes            NVARCHAR(500),
    created_at       DATETIME2 DEFAULT SYSDATETIME()
);

IF OBJECT_ID('maintenance_records', 'U') IS NULL
CREATE TABLE maintenance_records (
    id               INT PRIMARY KEY IDENTITY(1,1),
    lock_id          INT NOT NULL,
    maintenance_date DATE NOT NULL,
    maintenance_time TIME,
    technician       NVARCHAR(100),
    supervisor       NVARCHAR(100),
    maintenance_type NVARCHAR(50) DEFAULT 'Preventivo',
    quarter          TINYINT,
    year             SMALLINT,
    status           NVARCHAR(50) DEFAULT 'Realizado',
    annotations      NVARCHAR(MAX),
    created_at       DATETIME2 DEFAULT SYSDATETIME()
);

IF OBJECT_ID('locks', 'U') IS NULL
CREATE TABLE locks (
    id                INT PRIMARY KEY IDENTITY(1,1),
    sector_id         INT NOT NULL,
    room_code         NVARCHAR(20) NOT NULL,
    room_name         NVARCHAR(100),
    installation_date DATE,
    last_clock_config DATE,
    model             NVARCHAR(50) DEFAULT '790',
    serial_number     NVARCHAR(50),
    active            BIT DEFAULT 1,
    notes             NVARCHAR(MAX),
    created_at        DATETIME2 DEFAULT SYSDATETIME()
);

IF OBJECT_ID('sector_quarters', 'U') IS NULL
CREATE TABLE sector_quarters (
    id        INT PRIMARY KEY IDENTITY(1,1),
    sector_id INT NOT NULL,
    quarter   TINYINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    active    BIT DEFAULT 1,
    UNIQUE(sector_id, quarter)
);

IF OBJECT_ID('sectors', 'U') IS NULL
CREATE TABLE sectors (
    id          INT PRIMARY KEY IDENTITY(1,1),
    code        NVARCHAR(10) UNIQUE NOT NULL,
    name        NVARCHAR(100) NOT NULL,
    description NVARCHAR(500),
    active      BIT DEFAULT 1,
    created_at  DATETIME2 DEFAULT SYSDATETIME()
);

-- Foreign keys (only if they don't exist yet)
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_locks_sector')
    ALTER TABLE locks ADD CONSTRAINT FK_locks_sector FOREIGN KEY (sector_id) REFERENCES sectors(id);

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_sq_sector')
    ALTER TABLE sector_quarters ADD CONSTRAINT FK_sq_sector FOREIGN KEY (sector_id) REFERENCES sectors(id);

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_mr_lock')
    ALTER TABLE maintenance_records ADD CONSTRAINT FK_mr_lock FOREIGN KEY (lock_id) REFERENCES locks(id);

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_br_lock')
    ALTER TABLE battery_readings ADD CONSTRAINT FK_br_lock FOREIGN KEY (lock_id) REFERENCES locks(id);

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_cc_lock')
    ALTER TABLE clock_configs ADD CONSTRAINT FK_cc_lock FOREIGN KEY (lock_id) REFERENCES locks(id);

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_le_lock')
    ALTER TABLE lock_events ADD CONSTRAINT FK_le_lock FOREIGN KEY (lock_id) REFERENCES locks(id);
"""

# ---------- Seed data ----------
SECTORS = [
    ('100', 'Sector Cien',             'Habitaciones 100'),
    ('200', 'Sector Docientos',        'Habitaciones 200'),
    ('300', 'Sector Trecientos',       'Habitaciones 300'),
    ('400', 'Sector Cuatrocientos',    'Habitaciones 400'),
    ('500', 'Sector Quinientos / Salones', 'Habitaciones 500, Salones y áreas comunes'),
]

# sector_code → quarters list
SECTOR_QUARTERS = {
    '100': [1, 3],
    '200': [2, 4],
    '300': [1, 3],
    '400': [2, 4],
    '500': [2, 4],
}

# sector_code → list of (room_code, room_name or None)
LOCKS_SEED = {
    '100': [
        ('101',  None), ('102A', None), ('103',  None), ('104A', None),
        ('105',  None), ('106',  None), ('107',  None), ('108',  None),
        ('109',  None), ('110',  None), ('111',  None), ('112',  None),
        ('113',  None), ('114',  None), ('115',  None), ('116',  None),
        ('117',  None), ('118',  None), ('119',  None), ('120',  None),
    ],
    '200': [
        ('201',None),('202',None),('203',None),('204',None),('205',None),
        ('206',None),('207',None),('208',None),('209',None),('210',None),
        ('211',None),('212',None),('214',None),('215',None),('216',None),
        ('217',None),('218',None),('219',None),('220',None),('221',None),
        ('222',None),('223',None),('224',None),('225',None),
    ],
    '300': [
        ('305',None),('306',None),('307',None),('308',None),('309',None),
        ('310',None),('311',None),('312',None),('314',None),('316',None),
    ],
    '400': [
        ('401',None),('402',None),('403',None),('404',None),('405',None),
        ('406',None),('407',None),('408',None),('409',None),('410',None),
        ('411',None),('412',None),('414',None),('415',None),('416',None),
        ('417',None),('418',None),('419',None),('420',None),('421',None),
        ('422',None),('423',None),
    ],
    '500': [
        ('501',None),('502',None),('503',None),('504',None),('505',None),
        ('506',None),('507',None),('508',None),('509',None),('510',None),
        ('511',None),('512',None),('514',None),('515',None),('516',None),
        ('517',None),('518',None),('519',None),('520',None),('521',None),
        ('522',None),('523',None),('524',None),('525',None),('526',None),
        ('527',None),('528',None),('529',None),('530',None),('531',None),
        ('532',None),('533',None),('534',None),('535',None),('536',None),
        ('537',None),
        ('SL1', 'Salón Landívar 1'),
        ('SL2', 'Salón Landívar 2'),
        ('SL3', 'Salón Landívar 3'),
        ('SOB', 'Salón del Obispo'),
        ('SCU', 'Salón de la Cueva'),
        ('SDL', 'Salón Doña Luisa'),
        ('SDB', 'Salón Doña Beatriz'),
        ('SDP', 'Salón Don Pedro'),
        ('GYM', 'GYM'),
        ('P500','Puerta Entrada 500'),
    ],
}


def seed(conn):
    cur = conn.cursor()
    cur.execute("USE LockManager")

    for code, name, desc in SECTORS:
        cur.execute("SELECT id FROM sectors WHERE code = ?", code)
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO sectors (code, name, description) VALUES (?,?,?)",
            code, name, desc
        )
        print(f"  Sector {code} insertado")

    conn.commit()

    for code, quarters in SECTOR_QUARTERS.items():
        cur.execute("SELECT id FROM sectors WHERE code = ?", code)
        row = cur.fetchone()
        if not row:
            continue
        sid = row[0]
        for q in quarters:
            cur.execute("SELECT id FROM sector_quarters WHERE sector_id=? AND quarter=?", sid, q)
            if not cur.fetchone():
                cur.execute("INSERT INTO sector_quarters (sector_id, quarter) VALUES (?,?)", sid, q)

    conn.commit()

    for code, lock_list in LOCKS_SEED.items():
        cur.execute("SELECT id FROM sectors WHERE code = ?", code)
        row = cur.fetchone()
        if not row:
            continue
        sid = row[0]
        for room_code, room_name in lock_list:
            cur.execute("SELECT id FROM locks WHERE sector_id=? AND room_code=?", sid, room_code)
            if cur.fetchone():
                continue
            cur.execute(
                "INSERT INTO locks (sector_id, room_code, room_name, model) VALUES (?,?,?,?)",
                sid, room_code, room_name, '790'
            )
        print(f"  Locks sector {code} insertados")

    conn.commit()
    print("Seed completado.")


def main():
    print("Creando base de datos...")
    conn = get_master_conn()
    conn.execute(SCHEMA_SQL)
    conn.close()

    print("Creando tablas...")
    conn2 = get_master_conn()
    for stmt in TABLES_SQL.split('\n\n'):
        stmt = stmt.strip()
        if stmt:
            try:
                conn2.execute(stmt)
            except Exception as e:
                print(f"  (aviso) {e}")
    conn2.commit()

    print("Insertando datos iniciales...")
    seed(conn2)
    conn2.close()
    print("\nBase de datos lista. Ejecuta: python app.py")


if __name__ == '__main__':
    main()
