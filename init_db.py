import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

def init_db():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    # 1. Resetting the Appointments Calendar
    print("Dropping old calendar and starting fresh...")
    cursor.execute("DROP TABLE IF EXISTS appointments;")
    
    cursor.execute("""
        CREATE TABLE appointments (
            id SERIAL PRIMARY KEY,
            day VARCHAR(20),
            time_slot VARCHAR(20),
            is_booked INT DEFAULT 0,
            customer_name VARCHAR(100)
        );
    """)

    # 2. Setting up the Agent Memory (Sessions)
    print("Verifying sessions table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR(255) PRIMARY KEY,
            history_json TEXT
        );
    """)

    # 3. Setting up the Telemetry (Audit Logs)
    print("Verifying audit_logs table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGSERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            user_message TEXT,
            tool_name VARCHAR(255),
            tool_args JSONB,
            ai_output TEXT,
            latency_ms INT
        );
    """)

    # 4. Seeding the Calendar Data
    days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    time_slots = ["09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM"]

    print("Seeding new time slots...")
    for day in days:
        for slot in time_slots:
            cursor.execute(
                "INSERT INTO appointments (day, time_slot, is_booked) VALUES (%s, %s, 0)",
                (day, slot)
            )

    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ Database initialized! Added {len(days) * len(time_slots)} available time slots.")

if __name__ == "__main__":
    init_db()