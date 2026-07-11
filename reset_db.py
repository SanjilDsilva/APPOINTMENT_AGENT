import sqlite3
import os

current_directory = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_directory, ('schedule.db'))

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("UPDATE appointments SET is_booked = 0")
conn.commit()
conn.close()

print("Database reset! All appointments are now available.")