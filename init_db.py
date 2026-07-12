import psycopg2
from dotenv import load_dotenv
import os 

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
print("Connecting to Supabase PostgreSQL...")

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    day TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    is_booked INTEGER DEFAULT 0,
    customer_name TEXT DEFAULT NULL
)
''')

cursor.execute('''
CREATE TABLE sessions(
    session_id TEXT PRIMARY KEY,
    history_json TEXT NOT NULL
)
''')

cursor.execute(
    "INSERT INTO appointments (day, time_slot) VALUES (%s, %s)", 
    ('wednesday', '9:00 AM')
)

conn.commit()
conn.close()

print("Cloud database successfully initialized!")