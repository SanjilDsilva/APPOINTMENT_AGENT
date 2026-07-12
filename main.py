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


def book_appointment(day: str, time_slot: str, customer_name: str) -> str:
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
    
    cursor.execute("UPDATE appointments SET is_booked = 1, customer_name = ? WHERE day = ? AND time_slot = ?", (customer_name, day_lower, time_slot))

    conn.commit() 
    conn.close()
    
    return f"Success! I have booked the {time_slot} appointment on {day} for {customer_name}."

def cancel_appointment(day: str, time_slot: str, customer_name: str) -> str:
    """Cancels an existing appointment for a specific day and time."""
    day_lower = day.lower()

    current_directory = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_directory, ('schedule.db'))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT is_booked, customer_name FROM appointments WHERE day = ? AND time_slot = ? ", (day_lower, time_slot))
    result = cursor.fetchone()

    if result is None:
        conn.close()
        return f"I cannot find a {time_slot} slot on {day}."
    
    is_booked = result[0]
    db_customer_name = result[1]

    if is_booked == 0:
        conn.close()
        return f"The {time_slot} slot on {day} is already available."
    
    if db_customer_name is None or db_customer_name.lower() != customer_name.lower():
        conn.close()
        return f"Authorization failed. This appointment is booked under a different name, not {customer_name}."
    
    cursor.execute("UPDATE appointments SET is_booked = 0, customer_name = NULL WHERE day = ? AND time_slot = ?", (day_lower, time_slot))
    
    conn.commit()
    conn.close()

    return f"Success! I have canceled the {time_slot} appointment on {day} for {customer_name}."


# --- THE AGENT ---
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("Initializing AI Agent...")
chat = client.chats.create(
    model='gemini-3.1-flash-lite',
    config=types.GenerateContentConfig(
        tools=[check_availability, book_appointment, cancel_appointment],
        temperature=0.0,
        system_instruction=(
            "You are a professional scheduling assistant for a clinic. "
            "Rule 1: You MUST explicitly ask the user for their name before calling the book_appointment or cancel_appointment tools. "
            "Rule 2: NEVER guess, invent, or assume a user's name. If they haven't told you their name yet, stop and ask. "
            "Rule 3: Only answer questions related to scheduling appointments. If the user asks about anything else, politely decline."
        )
    )
)

# --- THE CHAT ---
print("Welcome to the Scheduling Agent. Type 'exit' to quit.")
while True:
    user_input = input("You: ")
    clean_input = user_input.lower().strip(" .")
    if clean_input in ['exit', 'quit']:
        break
    response = chat.send_message(user_input)
    print(f"AI: {response.text}")