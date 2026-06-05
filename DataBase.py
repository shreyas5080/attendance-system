import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SSL_CA = "/etc/ssl/certs/ca-certificates.crt"


def get_database_config():
    config = {
        "host": os.getenv("DB_HOST", "mysql-2b417a2d-shreyas5080.l.aivencloud.com"),
        "port": int(os.getenv("DB_PORT", "24706")),
        "user": os.getenv("DB_USER", "avnadmin"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME", "my_database"),
        "connection_timeout": int(os.getenv("DB_CONNECTION_TIMEOUT", "10")),
    }

    ssl_ca = os.getenv("DB_SSL_CA")
    if ssl_ca:
        config["ssl_ca"] = ssl_ca
    elif Path(DEFAULT_SSL_CA).exists():
        config["ssl_ca"] = DEFAULT_SSL_CA

    return config


def init_database():
<<<<<<< HEAD
    conn = mysql.connector.connect(
        host="mysql-2b417a2d-shreyas5080.l.aivencloud.com",
        port=24706,  
        user="avnadmin",
        password=os.getenv("DB_PASSWORD"),
        database="my_database",
        ssl_ca="/etc/ssl/certs/ca-certificates.crt"
    )
    return conn
=======
    return mysql.connector.connect(**get_database_config())


def column_exists(cur, table_name, column_name):
    cur.execute("""
        SELECT COUNT(*) AS column_count
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND COLUMN_NAME = %s
    """, (table_name, column_name))
    return cur.fetchone()[0] > 0


def index_exists(cur, table_name, index_name):
    cur.execute("""
        SELECT COUNT(*) AS index_count
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND INDEX_NAME = %s
    """, (table_name, index_name))
    return cur.fetchone()[0] > 0


def ensure_auth_schema():
    conn = init_database()
    cur = conn.cursor()
    try:
        user_columns = {
            "email": "ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL AFTER user_name",
            "auth_provider": "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(30) NOT NULL DEFAULT 'password' AFTER user_role",
            "oauth_subject": "ALTER TABLE users ADD COLUMN oauth_subject VARCHAR(255) NULL AFTER auth_provider",
            "is_verified": "ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0 AFTER oauth_subject",
            "last_login_at": "ALTER TABLE users ADD COLUMN last_login_at DATETIME NULL AFTER is_verified",
        }

        for column_name, ddl in user_columns.items():
            if not column_exists(cur, "users", column_name):
                cur.execute(ddl)

        indexes = {
            "idx_users_email_unique": "ALTER TABLE users ADD UNIQUE INDEX idx_users_email_unique (email)",
            "idx_users_oauth": "ALTER TABLE users ADD INDEX idx_users_oauth (auth_provider, oauth_subject)",
        }

        for index_name, ddl in indexes.items():
            if not index_exists(cur, "users", index_name):
                cur.execute(ddl)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS otp_verifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                user_name VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                otp_hash VARCHAR(255) NOT NULL,
                expires_at DATETIME NOT NULL,
                attempts INT NOT NULL DEFAULT 0,
                consumed_at DATETIME NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_otp_email (email),
                INDEX idx_otp_expires_at (expires_at)
            )
        """)

        conn.commit()
    finally:
        conn.close()


def check_database_health():
    conn = None
    try:
        conn = init_database()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        return True, "connected"
    except mysql.connector.Error as error:
        return False, str(error)
    finally:
        if conn and conn.is_connected():
            conn.close()
>>>>>>> c330c8394f72f53a9d9d3a8d327f41a20aa0fcf5
