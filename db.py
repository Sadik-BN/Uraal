import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))

def get_conn():
    conn = mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT")),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        time_zone="+06:00",
        ssl_ca=os.path.join(HERE, "db", "ca.pem"),
        ssl_verify_cert=True
    )
    cur = conn.cursor()
    cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    cur.close()
    return conn


def fetch_all(sql, params=()):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def run(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    cur.close()
    conn.close()