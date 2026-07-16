# 🤖 Enterprise Multi-Agent Scheduling AI

An enterprise-grade, multi-agent AI scheduling assistant built with **LangGraph**, **FastAPI**, and **PostgreSQL**. 

This project demonstrates the evolution of an LLM application from a simple conversational wrapper into a robust **Supervisor-Worker architecture**. It eliminates LLM hallucinations and standardizes database interactions by enforcing strict conditional routing, Python-level security guardrails, and real-time token streaming.

---

## 🚀 The Engineering Journey

This project was built iteratively to address the scaling and determinism challenges inherent in LLM application development.

### Phase 1: Proof of Concept (The Monolith)
*   **Stack:** Python, LangChain, SQLite3.
*   **Architecture:** A single, monolithic prompt attempting to handle greetings, routing, and tool calling simultaneously.
*   **Challenges:** The LLM struggled with state desynchronization and occasionally hallucinated database records because it lacked strict execution boundaries.

### Phase 2: Introduction of Tool Calling & State
*   **Stack:** FastAPI, LangChain Agents.
*   **Architecture:** Bound SQL-executing Python functions to the Gemini API using `@tool` decorators. 
*   **Challenges:** While tool execution improved, a single agent still struggled to gracefully handle missing parameters (like asking for a name before executing a cancellation tool).

### Phase 3: The Enterprise Migration (Current State)
*   **Stack:** LangGraph, PostgreSQL, Docker.
*   **Architecture:** Migrated from a monolithic agent to a **Multi-Agent Node Graph**. Replaced SQLite3 with PostgreSQL for production-ready data handling. Implemented an asynchronous backend with Server-Sent Events (SSE) for real-time token streaming to a custom Javascript frontend.
*   **Result:** A highly deterministic, secure, and user-friendly system.

---

## 🏗️ System Design & Architecture

This application implements several high-level backend engineering concepts to ensure reliability, security, and performance:

1. **Service-Oriented Architecture (Micro-Agents)**
   *   Instead of a monolithic prompt, tasks are decoupled into specialized micro-agents via **LangGraph**. The **Receptionist Node** handles read-only tasks and context gathering, while the **Scheduler Node** acts as an isolated, sandboxed worker with write/delete database privileges. A deterministic **Router** function acts as the API gateway between them.
2. **In-Memory Caching (State Management)**
   *   Session state and conversation history are cached in the server's RAM (simulating Redis behavior) mapping unique browser `session_id`s to LangGraph state dictionaries. This prevents redundant database lookups for chat history and reduces API latency.
3. **Optimistic Concurrency Control (OCC)**
   *   To prevent race conditions (e.g., two users booking the exact same time slot simultaneously), the database tools enforce state-checks at the SQL level (`WHERE time_slot = %s AND is_booked = 0`). This ensures ACID compliance and data integrity.
4. **Role-Based Access Control (RBAC)**
   *   The system operates on a "Zero Trust" model regarding the LLM. When an appointment is canceled, the LLM's payload is intercepted by a Python guardrail that queries the database to verify the user's provided name matches the database record before allowing the `UPDATE` execution.

---

## ✨ Key Features

*   **Multi-Agent Handoffs:** Seamless, context-aware transitions between front-desk and backend agents.
*   **Real-Time Token Streaming:** Asynchronous generator functions yield LLM tokens chunk-by-chunk to the frontend for a ChatGPT-like UX.
*   **Data Formatting Guardrails:** Python functions silently intercept and sanitize LLM arguments (e.g., standardizing "2:00 PM" to "02:00 PM") before SQL execution.
*   **Modern Frontend:** A responsive, session-isolated web interface built with vanilla HTML/CSS/JS that handles HTTP streaming.
*   **Fully Containerized:** Zero-configuration deployment using Docker and Docker Compose.

---

## 🛠️ Tech Stack

*   **Backend Framework:** FastAPI, Uvicorn
*   **AI/Orchestration:** LangGraph, LangChain, Google Gemini API (3.1-Flash-Lite)
*   **Database:** PostgreSQL, psycopg2-binary
*   **Frontend:** HTML5, CSS3, JavaScript (Fetch API + Streams)
*   **Infrastructure:** Docker, Docker Compose

---

## 💻 How to Run Locally

This project is fully containerized. You do not need a local PostgreSQL installation to run it.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/your-repo-name.git
   cd your-repo-name
   ```

2. **Set up your environment variables:**
   Create a `.env` file in the root directory and add your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```

3. **Build and start the Docker containers:**
   ```bash
   docker compose up -d --build
   ```

4. **Initialize the database:**
   Run the setup script inside the active API container to create the tables and seed initial availability:
   ```bash
   docker compose exec api python init_db.py
   ```

5. **Start chatting:**
   Open your browser and navigate to `http://localhost:8000` to interact with the agent.