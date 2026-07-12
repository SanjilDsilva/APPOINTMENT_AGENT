import sqlite3
import os

# 1. Lock down the exact file path
current_directory = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_directory, 'schedule.db')

# 2. Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 3. Create the table
# 3. Create the table
create_table_query = '''
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    is_booked INTEGER DEFAULT 0,
    customer_name TEXT DEFAULT NULL
)
'''
cursor.execute(create_table_query)

# 4. Insert sample data
sample_data = [
    ('wednesday', '9:00 AM'),
    ('wednesday', '11:30 AM'),
    ('wednesday', '4:00 PM'),
    ('friday', '10:00 AM'),
    ('friday', '3:00 PM')
]

cursor.executemany('''
    INSERT INTO appointments (day, time_slot) 
    VALUES (?, ?)
''', sample_data)

# 5. Save and Close
conn.commit()
conn.close()

print("Database 'schedule.db' created and populated successfully!")