import psycopg2
from psycopg2.extras import Json
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

def log_interaction(session_id: str, user_message: str, tool_name: str, tool_args: dict, ai_output: str, latency_ms: int):
    """
    Persists full conversation telemetry and tool usage execution metrics
    directly to the Supabase database for audit trails and cost monitoring.
    """

    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO audit_logs (session_id, user_message, tool_name, tool_args, ai_output, latency_ms)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            session_id, 
            user_message,
            tool_name if tool_name else None,
            Json(tool_args)  if tool_args else Json({}),
            ai_output,
            int(latency_ms)
        ))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"📊 [Telemetry] Logged session {session_id} successfully.")

    except Exception as e:
        print(f"⚠️ [Telemetry Error] Failed to write to audit log: {e}")