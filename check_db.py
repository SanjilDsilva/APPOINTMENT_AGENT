import sqlite3
import os

# Lock down the exact file path
current_directory = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_directory, 'schedule.db')

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# SELECT * means "Select ALL columns"
cursor.execute("SELECT * FROM appointments")
rows = cursor.fetchall()

print("--- CURRENT DATABASE STATE ---")
for row in rows:
    print(row)

conn.close()