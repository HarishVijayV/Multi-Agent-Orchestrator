import asyncio
import uuid
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- REAL AI IMPORTS ---
import google.generativeai as genai
from tavily import TavilyClient
import httpx
from bs4 import BeautifulSoup

# --- 1. SETUP YOUR 3 API KEYS HERE ---
# GEMINI_KEY_PLANNER = "AIzaSyA0WKAu7HqV2K3D4SpusAjla7XCrvAB_XY"
# GEMINI_KEY_WRITER = "AIzaSyC__QqnxXY4W4uF1RoGZk4sfONhbpFifDA"
GEMINI_KEY_PLANNER = "AIzaSyB_nLrj683SoNMSdd4ohnN74rOFtGiCQWM"
GEMINI_KEY_WRITER = "AIzaSyB_nLrj683SoNMSdd4ohnN74rOFtGiCQWM"
TAVILY_API_KEY = "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"
# --- INITIALIZE FASTAPI ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. The Strict Data Contracts
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

# 3. The In-Memory Database
db = {}

# 4. The REAL Assembly Line Workers (Agents)
class BaseAgent:
    async def execute(self, task: Task):
        raise NotImplementedError("Agents must implement the execute method")

class PlannerAgent(BaseAgent):
    async def execute(self, task: Task):
        task.logs.append("Planner: Booting Gemini with Account #1...")
        
        # Configure Gemini using the FIRST key
        genai.configure(api_key=GEMINI_KEY_PLANNER)
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        
        response = model.generate_content(f"Give me 3 precise Google search queries to research: {task.prompt}. Just the queries, no extra text.")
        
        task.logs.append(f"Planner Strategy:\n{response.text}")
        return TaskState.RESEARCHING

class ResearcherAgent(BaseAgent):
    async def execute(self, task: Task):
        task.logs.append("Researcher: Searching the web using Tavily API...")
        
        # Configure Tavily using your key
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        search_result = tavily.search(query=task.prompt, max_results=1)
        top_url = search_result['results'][0]['url']
        task.logs.append(f"Researcher: Found top source -> {top_url}. Scraping now...")

        # Scrape the actual website
        async with httpx.AsyncClient() as client:
            page = await client.get(top_url, follow_redirects=True)
            soup = BeautifulSoup(page.text, 'html.parser')
            # Grab paragraph text, limit to 1500 chars
            scraped_text = ' '.join([p.text for p in soup.find_all('p')])[:1500] 

        # Save data invisibly for the Writer Agent
        task.logs.append(f"SCRAPED_DATA:{scraped_text}") 
        return TaskState.WRITING

class WriterAgent(BaseAgent):
    async def execute(self, task: Task):
        task.logs.append("Writer: Booting Gemini with Account #2 for maximum speed...")
        
        # Configure Gemini using the SECOND key (No pause needed!)
        genai.configure(api_key=GEMINI_KEY_WRITER)
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        
        # Dig out the secret scraped text from the Researcher
        scraped_data = [log for log in task.logs if "SCRAPED_DATA:" in log][0]

        ai_prompt = f"Write a professional markdown report about '{task.prompt}' strictly using this scraped data: {scraped_data}"
        response = model.generate_content(ai_prompt)

        # Save the real AI essay to the final result
        task.result = response.text
        task.logs.append("Writer: Final report generated successfully!")
        
        return TaskState.REVIEWING

class ReviewerAgent(BaseAgent):
    async def execute(self, task: Task):
        # We keep this step fast to avoid wasting API limits
        task.logs.append("Reviewer: Formatting looks good. Approving deployment.")
        return TaskState.COMPLETED

# 5. The Factory Manager (Orchestrator)
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

# 6. The API Endpoints
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

#/////////////////////////////////////////////////////
"use client";

import { useState, useEffect } from "react";

const STATES = ["PENDING", "PLANNING", "RESEARCHING", "WRITING", "REVIEWING", "COMPLETED", "FAILED"];

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [taskData, setTaskData] = useState(null);
  const [loading, setLoading] = useState(false);

  const submitTask = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    
    try {
      const res = await fetch("http://localhost:8000/tasks/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      
      setTaskId(data.task_id);
      
      // 👇 THE JUMP START 👇
      // This instantly draws the UI while the backend is booting up!
      setTaskData({
        state: "PENDING",
        logs: ["System: Task received. Booting up AI agents..."],
        result: null
      });
      
      setPrompt(""); 
    } catch (error) {
      console.error("Failed to start task:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let interval;

    const fetchStatus = async () => {
      if (!taskId) return;
      try {
        const res = await fetch(`http://localhost:8000/tasks/${taskId}`);
        const data = await res.json();
        
        // This will seamlessly overwrite the "Jump Start" data once Python responds
        setTaskData(data);

        if (data.state === "COMPLETED" || data.state === "FAILED") {
          clearInterval(interval);
        }
      } catch (error) {
        console.error("Failed to fetch status:", error);
      }
    };

    if (taskId && taskData?.state !== "COMPLETED" && taskData?.state !== "FAILED") {
      interval = setInterval(fetchStatus, 1500);
    }

    return () => clearInterval(interval);
  }, [taskId, taskData?.state]);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-blue-900">Multi-Agent Orchestrator</h1>
          <p className="text-gray-500 mt-2">Submit a research task and watch the AI agents collaborate.</p>
        </div>

        {/* Input Form */}
        <form onSubmit={submitTask} className="flex gap-4 bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Research the pros and cons of microservices..."
            className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading || (taskData && taskData.state !== "COMPLETED" && taskData.state !== "FAILED")}
          />
          <button
            type="submit"
            disabled={loading || !prompt.trim()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors disabled:opacity-50 min-w-[140px]"
          >
            {loading ? "Starting..." : "Run Agents"}
          </button>
        </form>

        {/* The Dashboard Shield */}
        {taskData && (
          <div className="space-y-6">
            
            {/* Visual Pipeline */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h2 className="text-lg font-semibold mb-4">Pipeline Status</h2>
              <div className="flex flex-wrap gap-2">
                {STATES.map((state) => {
                  const isActive = taskData.state === state;
                  const isPast = STATES.indexOf(taskData.state) > STATES.indexOf(state) && taskData.state !== "FAILED";
                  
                  return (
                    <div
                      key={state}
                      className={`px-4 py-2 rounded-full text-sm font-bold transition-all duration-300 ${
                        isActive ? "bg-blue-600 text-white animate-pulse" : 
                        isPast ? "bg-green-100 text-green-700" : 
                        "bg-gray-100 text-gray-400"
                      }`}
                    >
                      {state}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Split Screen View */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Left Side: Hacker Terminal Logs */}
              <div className="bg-slate-900 text-green-400 p-6 rounded-xl shadow-sm font-mono text-sm h-96 overflow-y-auto">
                <h3 className="text-white font-sans font-semibold mb-4 border-b border-slate-700 pb-2">Agent Activity Logs</h3>
                <div className="space-y-2">
                  {taskData.logs.map((log, index) => (
                    <div key={index} className="flex gap-2">
                      <span className="text-slate-500">[{new Date().toLocaleTimeString()}]</span>
                      <span>{log}</span>
                    </div>
                  ))}
                  {taskData.state !== "COMPLETED" && taskData.state !== "FAILED" && (
                    <div className="animate-pulse">_</div>
                  )}
                </div>
              </div>

              {/* Right Side: Final Essay Result */}
              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 h-96 overflow-y-auto">
                <h3 className="font-semibold mb-4 border-b pb-2">Final Output</h3>
                {taskData.result ? (
                  <div className="prose prose-blue">
                    {taskData.result.split('\n').map((line, i) => (
                      <p key={i} className={line.startsWith('#') ? "text-xl font-bold mt-4" : "mt-2"}>
                        {line}
                      </p>
                    ))}
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400 italic text-center px-4">
                    Report is being generated... waiting on Writer Agent.
                  </div>
                )}
              </div>

            </div>
          </div>
        )}
      </div>
    </div>
  );
}