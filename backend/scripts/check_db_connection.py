import os
import psycopg


host = os.getenv("AFKMS_DB_HOST", "192.168.50.245")
port = int(os.getenv("AFKMS_DB_PORT", "5432"))
name = os.getenv("AFKMS_DB_NAME")
user = os.getenv("AFKMS_DB_USER")
password = os.getenv("AFKMS_DB_PASSWORD")

if not all([name, user, password]):
    raise SystemExit("Missing AFKMS_DB_NAME/AFKMS_DB_USER/AFKMS_DB_PASSWORD")

conn = psycopg.connect(host=host, port=port, dbname=name, user=user, password=password)
with conn.cursor() as cur:
    cur.execute("SELECT 1")
    value = cur.fetchone()[0]
print(f"DB connection ok: {value}")
conn.close()
