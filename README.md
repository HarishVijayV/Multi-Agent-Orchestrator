# Multi-Agent AI Orchestrator

An autonomous research system that coordinates specialized AI agents using a **Decoupled State-Machine Architecture**. The system transforms a single user prompt into a structured Markdown report by transitioning through a sequence of planning, live web-researching, and synthesis phases.

## Key Features

* **State-Machine Orchestration:** Strictly manages the task lifecycle (`PENDING` → `PLANNING` → `RESEARCHING` → `WRITING` →'REVIEWING'-> `COMPLETED`).
* **Agentic Intelligence:** Uses **Gemini 1.5 Flash** for strategic planning and content synthesis.
* **Real-time Web Grounding:** Integrates **Tavily API** and **BeautifulSoup** for live data extraction.
* **Asynchronous Backend:** Built with **FastAPI** to handle non-blocking I/O operations.
* **Live Activity Logs:** A terminal-style frontend that polls the backend to show real-time agent "thoughts" and status updates.

---

## Setup & Installation

### 1. Backend (Python/FastAPI)
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install required libraries
pip install fastapi uvicorn google-generativeai tavily-python httpx beautifulsoup4 python-dotenv
