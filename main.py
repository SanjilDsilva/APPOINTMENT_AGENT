import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import json
import psycopg2

# Load secret API key
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")




# --- THE TOOL ---
def check_availability(day: str) -> str:
    """Checks the database for available time_slots on a specific day."""
    print(f"Tool Call: Checking availability for {day}")
    
    # 2. Connect and Query
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT time_slot FROM appointments WHERE day = %s AND is_booked = 0", (day.lower(),))
    available_slots = cursor.fetchall()

    cursor.close()
    conn.close()

    # 3. Format Output
    if not available_slots:
        return f"No available slots on {day}."
    
    slots = [slot[0] for slot in available_slots]
    return f"Available slots on {day}: {', '.join(slots)}"


def book_appointment(day: str, time_slot: str, customer_name: str) -> str:
    """Books a time_slot for a customer."""
   
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT is_booked FROM appointments WHERE day = %s AND time_slot = %s", (day.lower(), time_slot))
    result = cursor.fetchone()

    if result is None:
        cursor.close()
        conn.close()
        return f"Error: The slot {time_slot} on {day} does not exist in the system."    

    if result[0] == 1:
        cursor.close()
        conn.close()
        return f"Sorry, {time_slot} on {day} is already booked."
    
    cursor.execute("UPDATE appointments SET is_booked = 1, customer_name = %s WHERE day = %s AND time_slot = %s", (customer_name, day.lower(), time_slot))

    conn.commit()

    cursor.close() 
    conn.close()
    
    return f"Successfully booked {time_slot} on {day} for {customer_name}!"

def cancel_appointment(day: str, time_slot: str, customer_name: str) -> str:
    """Cancels an existing appointment for a specific day and time."""

    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT is_booked, customer_name FROM appointments WHERE day = %s AND time_slot = %s ", (day.lower(), time_slot))
    result = cursor.fetchone()

    if result is None:
        cursor.close()
        conn.close()
        return f"Error: The slot {time_slot} on {day} does not exist in the system."
    
    if result[0] == 0:
        cursor.close()
        conn.close()
        return f"The slot {time_slot} on {day} is already available. Nothing to cancel."
    cursor.execute(
        "UPDATE appointments SET is_booked = 0, customer_name = NULL WHERE day = %s AND time_slot = %s",
        (day.lower(), time_slot)
    )
    
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return f"Successfully canceled the appointment for {time_slot} on {day}."

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
app = FastAPI(title="Scheduling AI Agent API")

class ChatRequest(BaseModel):
    session_id: str
    message: str

agent_config = types.GenerateContentConfig(
    tools = [check_availability, book_appointment, cancel_appointment],
    temperature=0.0,
    system_instruction=(
        "You are a professional scheduling assistant for a clinic. "
        "Rule 1: You MUST explicitly ask the user for their name before calling the book_appointment or cancel_appointment tools. "
        "Rule 2: NEVER guess, invent, or assume a user's name. If they haven't told you their name yet, stop and ask. "
        "Rule 3: Only answer questions related to scheduling appointments. If the user asks about anything else, politely decline."
    
    )
)

def load_history(session_id: str):
    """Retrieves and deserializes the chat history from PostgreSQL."""

    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT history_json FROM sessions WHERE session_id = %s", (session_id, ))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        raw_list = json.loads(result[0])
        return [types.Content(**item) for item in raw_list]
    return None

def save_history(session_id: str, history_list):
    """Serializes the chat history and saves it to PostgreSQL."""
    history_json = json.dumps([item.model_dump(mode="json", exclude_none=True) for item in history_list])

    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    cursor.execute("""INSERT INTO sessions (session_id, history_json) VALUES (%s, %s) ON CONFLICT (session_id) DO UPDATE SET history_json = EXCLUDED.history_json""", (session_id, history_json))

    conn.commit()
    cursor.close()
    conn.close()

@app.post("/chat")
def chat_with_agent(request: ChatRequest):
    """The Load -> Predict -> Save loop."""
    try:
        past_history = load_history(request.session_id)

        chat = client.chats.create(
            model = "gemini-3.1-flash-lite",
            config=agent_config,
            history=past_history
        )

        response = chat.send_message(request.message)

        save_history(request.session_id, chat.get_history())

        return {"reply": response.text}
    except Exception as e:
        return {"error": str(e)}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)