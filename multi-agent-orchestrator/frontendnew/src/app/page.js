
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
/////////////////////
//////////////////////////
//////////////////////////
/////////////////////
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