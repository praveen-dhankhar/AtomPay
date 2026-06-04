"""FastAPI entry point for the AtomPay AI Agent microservice.

Exposes a POST /chat endpoint that the Node.js backend proxies to.
Handles conversation history per user session for contextual responses.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from collections import defaultdict

from config import PORT
from db import close_db
from agent import chat_with_agent


# ── In-memory conversation history (per user) ──
conversation_histories: dict[str, list] = defaultdict(list)
MAX_HISTORY_PER_USER = 20  # Keep last 20 messages for context


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("[*] AtomPay AI Agent starting up...")
    yield
    print("[*] Shutting down AI Agent...")
    await close_db()


app = FastAPI(
    title="AtomPay AI Agent",
    description="Intelligent financial assistant for AtomPay",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──

class ChatRequest(BaseModel):
    message: str
    user_id: str


class ChatResponse(BaseModel):
    response: str
    user_id: str


class ClearHistoryRequest(BaseModel):
    user_id: str


# ── Endpoints ──

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "AtomPay AI Agent"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """Main chat endpoint — receives user messages and returns AI responses."""

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="User ID is required")

    try:
        # Get conversation history for context
        history = conversation_histories[req.user_id]

        # Convert history to LangChain message format
        from langchain_core.messages import HumanMessage, AIMessage
        chat_history = []
        for entry in history:
            if entry["role"] == "user":
                chat_history.append(HumanMessage(content=entry["content"]))
            else:
                chat_history.append(AIMessage(content=entry["content"]))

        # Get AI response
        response = await chat_with_agent(req.user_id, req.message, chat_history)

        # Store in history
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": response})

        # Trim history if too long
        if len(history) > MAX_HISTORY_PER_USER * 2:
            conversation_histories[req.user_id] = history[-(MAX_HISTORY_PER_USER * 2):]

        return ChatResponse(response=response, user_id=req.user_id)

    except Exception as e:
        print(f"Agent error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI Agent encountered an error. Please try again."
        )


@app.post("/clear-history")
async def clear_history(req: ClearHistoryRequest):
    """Clear conversation history for a user."""
    if req.user_id in conversation_histories:
        del conversation_histories[req.user_id]
    return {"status": "cleared", "user_id": req.user_id}


@app.get("/capabilities")
async def get_capabilities():
    """Return the agent's capabilities for the frontend to display."""
    return {
        "capabilities": [
            {
                "id": "balance",
                "icon": "💰",
                "title": "Wallet & Balance",
                "description": "Check your balance, wallet status, and currency",
                "sample_queries": ["What's my balance?", "Is my wallet active?"]
            },
            {
                "id": "transactions",
                "icon": "📋",
                "title": "Transaction History",
                "description": "View, search, and filter your payment history",
                "sample_queries": ["Show my last 5 transactions", "Find payments to @john"]
            },
            {
                "id": "expenses",
                "icon": "📊",
                "title": "Expense Tracker",
                "description": "Analyze spending patterns — daily, weekly, monthly breakdowns",
                "sample_queries": ["How much did I spend this week?", "Show my spending analysis"]
            },
            {
                "id": "insights",
                "icon": "🔍",
                "title": "Financial Insights",
                "description": "Top recipients, spending trends, net cash flow analysis",
                "sample_queries": ["Who do I send money to the most?", "What's my net cash flow?"]
            },
            {
                "id": "limits",
                "icon": "🛡️",
                "title": "Daily Limit Monitor",
                "description": "Track your ₹1,00,000 daily transfer limit usage",
                "sample_queries": ["How much daily limit is left?", "Can I send ₹50,000 more today?"]
            },
            {
                "id": "tips",
                "icon": "💡",
                "title": "Expense Control Tips",
                "description": "Personalized budgeting, saving, and investing techniques",
                "sample_queries": ["How can I save more money?", "Give me budgeting tips"]
            },
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
