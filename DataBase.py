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
    return mysql.connector.connect(**get_database_config())


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
