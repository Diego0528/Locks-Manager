"""
Migra usuarios de config.py a la tabla users en SQL Server.
Ejecutar UNA VEZ: python add_users_table.py
"""
import pyodbc
from config import Config


def get_conn():
    return pyodbc.connect(
        f"DRIVER={{{Config.DB_DRIVER}}};"
        f"SERVER={Config.DB_SERVER};"
        f"DATABASE={Config.DB_NAME};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )


CREATE_TABLE = """
IF OBJECT_ID('users', 'U') IS NULL
CREATE TABLE users (
    id         INT PRIMARY KEY IDENTITY(1,1),
    username   NVARCHAR(50)  UNIQUE NOT NULL,
    password   NVARCHAR(100) NOT NULL,
    full_name  NVARCHAR(100) NOT NULL,
    role       NVARCHAR(20)  DEFAULT 'technician',
    active     BIT           DEFAULT 1,
    created_at DATETIME2     DEFAULT SYSDATETIME()
);
"""


def main():
    conn = get_conn()
    cur = conn.cursor()

    print("Creando tabla users...")
    cur.execute(CREATE_TABLE)
    conn.commit()

    print("Migrando usuarios de config.py...")
    for username, data in Config.USERS.items():
        cur.execute("SELECT id FROM users WHERE username=?", username)
        if cur.fetchone():
            print(f"  {username} ya existe, omitido.")
            continue
        role = 'admin' if username == 'admin' else 'technician'
        cur.execute(
            "INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
            username, data['password'], data['full_name'], role
        )
        print(f"  {username} ({data['full_name']}) creado.")

    conn.commit()
    conn.close()
    print("\nListo. Usuarios en BD:")
    conn2 = get_conn()
    cur2 = conn2.cursor()
    cur2.execute("SELECT username, full_name, role, active FROM users ORDER BY id")
    for row in cur2.fetchall():
        print(f"  {row[0]:15} {row[1]:25} {row[2]:15} {'activo' if row[3] else 'inactivo'}")
    conn2.close()


if __name__ == "__main__":
    main()
