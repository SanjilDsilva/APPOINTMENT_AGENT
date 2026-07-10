import os
import sqlite3
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load secret API key
load_dotenv()

# --- THE TOOL ---
def check_availability(day: str) -> str:
    """Checks the database for available appointment times on a specific day."""
    day_lower = day.lower()
    
    # 1. Lock down the exact file path
    current_directory = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_directory, 'schedule.db')
    
    # 2. Connect and Query
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT time_slot FROM appointments WHERE day = ? AND is_booked = 0", (day_lower,))
    results = cursor.fetchall()
    conn.close()
    
    # 3. Format Output
    if results:
        times = [row[0] for row in results]
        return f"Available slots on {day}: {', '.join(times)}"
    else:
        return f"I cannot find any available slots for {day}."


def book_appointment(day: str, time_slot: str) -> str:
    """Books an appointment for a specific day and time."""
    day_lower = day.lower()
    
    current_direcory = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_direcory, 'schedule.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT is_booked FROM appointments WHERE day = ? AND time_slot = ?", (day_lower, time_slot))
    result = cursor.fetchone()

    if result is None:
        conn.close()
        return f"I cannot find a {time_slot} slot on {day}."
    
    is_booked = result[0]

    if is_booked == 1:
        conn.close()
        return f"Sorry, the {time_slot} slot on {day} is already taken."
    
    cursor.execute("UPDATE appointments SET is_booked = 1 WHERE day = ? AND time_slot = ?", (day_lower, time_slot))

    conn.commit() 
    conn.close()
    
    return f"Success! I have booked the {time_slot} appointment on {day} for you."

# --- THE AGENT ---
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("Initializing AI Agent...")
chat = client.chats.create(
    model='gemini-3.1-flash-lite',
    config=types.GenerateContentConfig(
        tools=[check_availability, book_appointment],
        temperature=0.0
    )
)

# --- THE CHAT ---
user_prompt = "I would like to book the 9:00 AM slot on Wednesday, please."
print(f"User: {user_prompt}")
print("AI is thinking...\n")

response = chat.send_message(user_prompt)

print(f"AI: {response.text}")