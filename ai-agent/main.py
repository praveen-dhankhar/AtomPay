"""FastAPI entry point for the AtomAI microservice.

Exposes:
  - POST /chat            — conversational assistant (DeepSeek + tools + verification)
  - POST /analytics       — deterministic analytics bundle (no LLM, no hallucination)
  - memory endpoints      — read/clear short-term per-user memory, set budget/goal

The Node.js backend proxies these, injecting the authenticated userId.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from collections import defaultdict

from config import PORT
import db
import memory
from agent import chat_with_agent


# ── In-memory conversation history (per user) ──
conversation_histories: dict[str, list] = defaultdict(list)
MAX_HISTORY_PER_USER = 20  # Keep last 20 messages for context


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("[*] AtomAI starting up...")
    yield
    print("[*] Shutting down AtomAI...")
    await db.close_db()


app = FastAPI(
    title="AtomAI",
    description="Intelligent financial assistant for AtomPay",
    version="2.0.0",
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


class UserRequest(BaseModel):
    user_id: str


class AnalyticsRequest(BaseModel):
    user_id: str
    period_days: int = 30


class BudgetRequest(BaseModel):
    user_id: str
    monthly_budget: float


class SavingsGoalRequest(BaseModel):
    user_id: str
    label: str
    target: float


# ── Helpers ──

async def _resolve_name(user_id: str) -> str:
    """Best-effort display name for greetings/personalization."""
    try:
        user = await db.get_user_by_id(user_id)
        if user:
            return user.get("name") or user.get("username") or ""
    except Exception:
        pass
    return ""


# ── Endpoints ──

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "AtomAI"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """Main chat endpoint — receives user messages and returns AI responses."""

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="User ID is required")

    try:
        from langchain_core.messages import HumanMessage, AIMessage

        history = conversation_histories[req.user_id]
        chat_history = []
        for entry in history:
            if entry["role"] == "user":
                chat_history.append(HumanMessage(content=entry["content"]))
            else:
                chat_history.append(AIMessage(content=entry["content"]))

        user_name = await _resolve_name(req.user_id)
        response = await chat_with_agent(req.user_id, req.message, chat_history, user_name)

        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": response})
        if len(history) > MAX_HISTORY_PER_USER * 2:
            conversation_histories[req.user_id] = history[-(MAX_HISTORY_PER_USER * 2):]

        return ChatResponse(response=response, user_id=req.user_id)

    except Exception as e:
        print(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail="AtomAI encountered an error. Please try again.")


@app.post("/clear-history")
async def clear_history(req: UserRequest):
    """Clear conversation history for a user."""
    conversation_histories.pop(req.user_id, None)
    return {"status": "cleared", "user_id": req.user_id}


@app.post("/analytics")
async def analytics_endpoint(req: AnalyticsRequest):
    """Deterministic analytics bundle — computed directly from MongoDB, NO LLM.

    This powers the dashboards (Expenses / Insights) reliably: numbers come
    straight from aggregation pipelines, so there is zero hallucination risk.
    """
    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="User ID is required")

    wallet = await db.get_wallet_by_user_id(req.user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet_id = wallet["_id"]
    days = max(1, min(req.period_days, 90))

    spending = await db.get_spending_aggregation(wallet_id, days)
    comparison = await db.compare_periods(wallet_id, days)
    recurring = await db.detect_recurring_payments(wallet_id, max(days, 90))
    forecast = await db.forecast_cashflow(wallet_id)
    daily_limit = await db.get_daily_limit_usage(wallet_id)

    mem = memory.get_memory(req.user_id)
    budget = mem.get("monthly_budget")
    month_spend = await db.get_current_month_spend(wallet_id)
    budget_status = None
    if budget:
        budget_status = {
            "monthly_budget": budget,
            "spent_this_month": month_spend,
            "remaining": round(budget - month_spend, 2),
            "percentage_used": round((month_spend / budget) * 100, 1) if budget else 0,
            "projected_month_spend": forecast["projected_month_spend"],
            "on_track": forecast["projected_month_spend"] <= budget,
        }

    return {
        "period_days": days,
        "spending": spending,
        "comparison": comparison,
        "recurring": recurring,
        "forecast": forecast,
        "daily_limit": daily_limit,
        "budget": budget_status,
        "savings_goal": mem.get("savings_goal"),
        "balance": wallet.get("balance", 0),
        "currency": wallet.get("currency", "INR"),
        "wallet_status": wallet.get("status", "Active"),
    }


# ── Memory endpoints ──

@app.post("/memory")
async def get_user_memory(req: UserRequest):
    """Return the short-term memory currently held for a user."""
    return {"user_id": req.user_id, "memory": memory.get_memory(req.user_id)}


@app.post("/memory/budget")
async def set_budget(req: BudgetRequest):
    memory.set_monthly_budget(req.user_id, req.monthly_budget)
    return {"status": "ok", "memory": memory.get_memory(req.user_id)}


@app.post("/memory/savings-goal")
async def set_savings_goal(req: SavingsGoalRequest):
    memory.set_savings_goal(req.user_id, req.label, req.target)
    return {"status": "ok", "memory": memory.get_memory(req.user_id)}


@app.post("/memory/clear")
async def clear_user_memory(req: UserRequest):
    memory.clear_memory(req.user_id)
    return {"status": "cleared", "user_id": req.user_id}


@app.get("/capabilities")
async def get_capabilities():
    """Return the agent's capabilities for the frontend to display."""
    return {
        "capabilities": [
            {"id": "balance", "icon": "💰", "title": "Wallet & Balance",
             "description": "Check your balance, wallet status, and currency",
             "sample_queries": ["What's my balance?", "Is my wallet active?"]},
            {"id": "transactions", "icon": "📋", "title": "Transaction History",
             "description": "View, search, and filter your payment history",
             "sample_queries": ["Show my last 5 transactions", "Find payments to @john"]},
            {"id": "expenses", "icon": "📊", "title": "Expense Tracker",
             "description": "Analyze spending patterns — daily, weekly, monthly breakdowns",
             "sample_queries": ["How much did I spend this week?", "Show my spending analysis"]},
            {"id": "trends", "icon": "📈", "title": "Trends & Forecast",
             "description": "Month-over-month trends and a forecast of your month-end spend",
             "sample_queries": ["Am I spending more than last month?", "Forecast my spending"]},
            {"id": "recurring", "icon": "🔁", "title": "Recurring Payments",
             "description": "Detect subscriptions and regular transfers",
             "sample_queries": ["What subscriptions do I have?", "Where does my money go regularly?"]},
            {"id": "budget", "icon": "🎯", "title": "Budget & Goals",
             "description": "Set a monthly budget or savings goal and track progress",
             "sample_queries": ["Set my monthly budget to 20000", "Am I on track this month?"]},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
