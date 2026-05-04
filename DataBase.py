import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()
def init_database():
    conn = mysql.connector.connect(
        host="mysql-2b417a2d-shreyas5080.l.aivencloud.com",
        port=24706,  
        user="avnadmin",
        password=os.getenv("DB_PASSWORD"),
        database="my_database",
        ssl_ca="C:/Users/Shreyas/Downloads/ca (1).pem"
    )
    return conn