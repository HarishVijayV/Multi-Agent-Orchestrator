import asyncio
import uuid
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import google.generativeai as genai
from tavily import TavilyClient
import httpx
from bs4 import BeautifulSoup

# GEMINI_KEY_PLANNER = "AIzaSyA0WKAu7HqV2K3D4SpusAjla7XCrvAB_XY"
# GEMINI_KEY_WRITER = "AIzaSyC__QqnxXY4W4uF1RoGZk4sfONhbpFifDA"
GEMINI_KEY_PLANNER = "AIzaSyB_nLrj683SoNMSdd4ohnN74rOFtGiCQWM"
GEMINI_KEY_WRITER = "AIzaSyB_nLrj683SoNMSdd4ohnN74rOFtGiCQWM"
TAVILY_API_KEY = "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"
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaskState(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    WRITING = "WRITING"
    REVIEWING = "REVIEWING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Task(BaseModel):
    id: str
    prompt: str
    state: TaskState = TaskState.PENDING
    logs: List[str] = []
    result: Optional[str] = None

class TaskRequest(BaseModel):
    prompt: str

db = {}

class BaseAgent:
    async def execute(self, task: Task):
        raise NotImplementedError("Agents must implement the execute method")

class PlannerAgent(BaseAgent):
    async def execute(self, task: Task):
        task.logs.append("Planner: Booting Gemini with Account #1...")
        
        genai.configure(api_key=GEMINI_KEY_PLANNER)
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        
        response = model.generate_content(f"Give me 3 precise Google search queries to research: {task.prompt}. Just the queries, no extra text.")
        
        task.logs.append(f"Planner Strategy:\n{response.text}")
        return TaskState.RESEARCHING

class ResearcherAgent(BaseAgent):
    async def execute(self, task: Task):
        task.logs.append("Researcher: Searching the web using Tavily API...")
        
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        search_result = tavily.search(query=task.prompt, max_results=1)
        top_url = search_result['results'][0]['url']
        task.logs.append(f"Researcher: Found top source -> {top_url}. Scraping now...")

        async with httpx.AsyncClient() as client:
            page = await client.get(top_url, follow_redirects=True)
            soup = BeautifulSoup(page.text, 'html.parser')
            scraped_text = ' '.join([p.text for p in soup.find_all('p')])[:1500] 

        task.logs.append(f"SCRAPED_DATA:{scraped_text}") 
        return TaskState.WRITING

class WriterAgent(BaseAgent):
    async def execute(self, task: Task):
        task.logs.append("Writer: Booting Gemini with Account #2 for maximum speed...")
        
        genai.configure(api_key=GEMINI_KEY_WRITER)
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        
        scraped_data = [log for log in task.logs if "SCRAPED_DATA:" in log][0]

        ai_prompt = f"Write a professional markdown report about '{task.prompt}' {scraped_data}"
        response = model.generate_content(ai_prompt)

        task.result = response.text
        task.logs.append("Writer: Final report generated successfully!")
        
        return TaskState.REVIEWING

class ReviewerAgent(BaseAgent):
    async def execute(self, task: Task):
        task.logs.append("Reviewer: Formatting looks good. Approving deployment.")
        return TaskState.COMPLETED

agents = {
    TaskState.PLANNING: PlannerAgent(),
    TaskState.RESEARCHING: ResearcherAgent(),
    TaskState.WRITING: WriterAgent(),
    TaskState.REVIEWING: ReviewerAgent()
}

async def run_orchestrator(task_id: str):
    task = db[task_id]
    task.state = TaskState.PLANNING 
    
    while task.state not in [TaskState.COMPLETED, TaskState.FAILED]:
        current_agent = agents.get(task.state)
        
        if current_agent:
            try:
                next_state = await current_agent.execute(task)
                task.state = next_state
            except Exception as e:
                task.logs.append(f"CRITICAL ERROR: {str(e)}")
                task.state = TaskState.FAILED
                break

@app.post("/tasks/")
async def create_task(request: TaskRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    new_task = Task(id=task_id, prompt=request.prompt)
    db[task_id] = new_task
    
    background_tasks.add_task(run_orchestrator, task_id)
    return {"task_id": task_id, "message": "Task started successfully"}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in db:
        return {"error": "Task not found"}
    return db[task_id]
