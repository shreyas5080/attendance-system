import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()
def init_database():
    conn = mysql.connector.connect(
        host = "localhost",
        port = 3306,
        user = "root",
        password = os.getenv("DB_PASSWORD"),
        database = "my_database"
    )
    return conn