import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

cursor.execute("UPDATE appointments SET is_booked = 0, customer_name = NULL")
conn.commit()

cursor.close()
conn.close()

print("Database reset! All appointments are now available.")