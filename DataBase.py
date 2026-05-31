import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()


def init_database():
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME", "my_database"),
    }

    ssl_ca = os.getenv("DB_SSL_CA")
    if ssl_ca:
        config["ssl_ca"] = ssl_ca

    return mysql.connector.connect(**config)
