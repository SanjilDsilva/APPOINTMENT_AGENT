import os
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# LangChain & LangGraph Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing import Annotated, Literal
from typing_extensions import TypedDict

# Load secret API key
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# Initialize FastAPI
app = FastAPI(title="Scheduling AI Agent API")

# ==========================================
# 1. INITIALIZE LLM (Must be at the top!)
# ==========================================
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)

# ==========================================
# 2. DEFINE TOOLS
# ==========================================
@tool
def check_availability(day: str) -> str:
    """Checks the database for available time_slots on a specific day."""
    print(f"Tool Call: Checking availability for {day}")
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT time_slot FROM appointments WHERE day = %s AND is_booked = 0", (day.lower(),))
    available_slots = cursor.fetchall()
    cursor.close()
    conn.close()

    if not available_slots:
        return f"No available slots on {day}."
    slots = [slot[0] for slot in available_slots]
    return f"Available slots on {day}: {', '.join(slots)}"

@tool
def check_my_appointment(customer_name: str) -> str:
    """Looks up existing booked appointments for a specific customer."""
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    # FIX: Added the comma to make it a valid tuple!
    cursor.execute("SELECT day, time_slot FROM appointments WHERE LOWER(customer_name) = LOWER(%s) AND is_booked = 1", (customer_name,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    if not results:
        return f"No appointments found for {customer_name}."
    appointments = [f"{row[0].capitalize()} at {row[1]}" for row in results]
    return f"Found the following appointments for {customer_name}: {', '.join(appointments)}"

@tool
def transfer_to_scheduler(customer_name: str, intent: str) -> str:
    """
    REQUIRED to book or cancel an appointment.
    Transfers the user to the scheduling department. 
    Intent must be 'book' or 'cancel'.
    """
    return "Routing to scheduler..."

@tool
def process_booking(customer_name: str, day: str, time_slot: str) -> str:
    """Books the appointment in the database."""

    time_slot = time_slot.strip().upper()
    if len(time_slot) == 7 and time_slot[1] == ":":
        time_slot = "0" + time_slot

    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE appointments
        SET is_booked = 1, customer_name = %s
        WHERE LOWER(day) = LOWER(%s) AND time_slot = %s AND is_booked = 0
        RETURNING id
    """, (customer_name, day, time_slot))
    result = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    if result:
        return f"Successfully booked {day} at {time_slot} for {customer_name}."
    return "Failed to book. That slot might be taken or invalid."

@tool
def cancel_appointment(day: str, time_slot: str, customer_name: str) -> str:
    """Cancels an existing appointment for a specific day and time."""

    time_slot = time_slot.strip().upper()
    if len(time_slot) == 7 and time_slot[1] == ":":
        time_slot = "0" + time_slot
    
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT is_booked, customer_name FROM appointments WHERE day = %s AND time_slot = %s", (day.lower(), time_slot))
    result = cursor.fetchone()

    if result is None:
        cursor.close()
        conn.close()
        return f"Error: The slot {time_slot} on {day} does not exist in the system."
    
    if result[0] == 0:
        cursor.close()
        conn.close()
        return f"The slot {time_slot} on {day} is already available. Nothing to cancel."
    
    db_customer_name = result[1]
    if db_customer_name and db_customer_name.lower() != customer_name.lower():
        cursor.close()
        conn.close()
        return f"Security Error: The name '{customer_name}' does not match the record for this appointment. Cancellation denied."
    
    cursor.execute(
        "UPDATE appointments SET is_booked = 0, customer_name = NULL WHERE day = %s AND time_slot = %s", (day.lower(), time_slot)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return f"Successfully canceled the appointment for {time_slot} on {day}."

# ==========================================
# 3. GRAPH STATE & AGENT BINDING
# ==========================================
# FIX: Used square brackets for Annotated
class State(TypedDict):
    messages: Annotated[list, add_messages]

receptionist_agent = llm.bind_tools([check_availability, check_my_appointment, transfer_to_scheduler])
scheduler_agent = llm.bind_tools([process_booking, cancel_appointment])

# ==========================================
# 4. GRAPH NODES & ROUTER
# ==========================================
def receptionist_node(state: State):
    sys_msg = SystemMessage(content=(
        "You are the front-desk receptionist. "
        "Rule 1: Answer availability questions using check_availability. "
        "Rule 2: Look up appointments using check_my_appointment. "
        "Rule 3: To book or cancel, you MUST ask for their name first. "
        "Rule 4: Once you have their name and intent, use the transfer_to_scheduler tool. "
        "Rule 5: Only answer scheduling questions."
    ))
    response = receptionist_agent.invoke([sys_msg] + state["messages"])
    return {"messages": [response]}

def router(state: State) -> Literal["tools", "scheduler", "__end__"]:
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return "__end__"
    
    tool_name = last_message.tool_calls[0]["name"]
    if tool_name == "transfer_to_scheduler":
        return "scheduler"
    return "tools"

def scheduler_node(state: State):
    sys_msg = SystemMessage(content="You are the scheduling agent. Use your process_booking tool to fulfill the requested booking. Be brief and confirm success or failure to the user.")
    last_msg = state["messages"][-1]
    tool_call = last_msg.tool_calls[0]

    tool_confirmation = ToolMessage(
        content="Transferred successfully to scheduler.",
        tool_call_id=tool_call["id"]
    )
    handoff_instruction = HumanMessage(
        content=f"Please process this request for {tool_call['args']['customer_name']}: {tool_call['args']['intent']}"
    )
    
    response = scheduler_agent.invoke([sys_msg] + state["messages"] + [tool_confirmation, handoff_instruction])
    return {"messages": [tool_confirmation, handoff_instruction, response]}

# ==========================================
# 5. BUILD THE GRAPH
# ==========================================
workflow = StateGraph(State)
workflow.add_node("receptionist", receptionist_node)
workflow.add_node("scheduler", scheduler_node)
workflow.add_node("tools", ToolNode([check_availability, check_my_appointment, process_booking, cancel_appointment]))

workflow.add_edge(START, "receptionist")
workflow.add_conditional_edges("receptionist", router)
workflow.add_edge("tools", "receptionist")
workflow.add_conditional_edges("scheduler", router)

app_graph = workflow.compile()

# ==========================================
# 6. FASTAPI ENDPOINTS
# ==========================================
class ChatRequest(BaseModel):
    session_id: str
    message: str

memory_store = {}

@app.get("/")
def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/chat")
def chat(request: ChatRequest):
    if request.session_id not in memory_store:
        memory_store[request.session_id] = {"messages": []}

    state = memory_store[request.session_id]
    state["messages"].append(HumanMessage(content=request.message))

    def event_generator():
        new_messages = [] # Keep track of the new messages to save later
        
        # Stream the chunks
        for chunk, metadata in app_graph.stream(state, stream_mode="messages"):
            new_messages.append(chunk) # Save to our local list
            
            if chunk.content and metadata.get("langgraph_node") in ["receptionist", "scheduler"]:
                raw_content = chunk.content
                
                # --- THE FIX: Gemini List Extraction ---
                if isinstance(raw_content, list):
                    text_chunk = "".join([block.get("text", "") for block in raw_content if isinstance(block, dict)])
                else:
                    text_chunk = str(raw_content)
                
                # Yield the clean string to the frontend
                if text_chunk:
                    yield text_chunk
                    
        # Update memory store using the chunks we collected 
        # (This avoids calling invoke() a second time!)
        memory_store[request.session_id]["messages"].extend(new_messages)

    return StreamingResponse(event_generator(), media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)