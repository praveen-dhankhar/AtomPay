"""LangChain Tools for the AtomPay AI Agent.

Each tool wraps a database query and returns human-readable results
that the LLM can use to answer user questions.
"""

import json
from langchain_core.tools import tool


# ── Tool 1: Check Wallet Balance ──

@tool
async def check_balance(user_id: str) -> str:
    """Check the user's current wallet balance, currency, and wallet status.
    Use this when the user asks about their balance, how much money they have, or wallet status.
    """
    from db import get_wallet_by_user_id, get_user_by_id

    user = await get_user_by_id(user_id)
    wallet = await get_wallet_by_user_id(user_id)

    if not wallet:
        return "Wallet not found. The user may not have set up their wallet yet."

    return json.dumps({
        "name": user.get("name", "") if user else "",
        "username": user.get("username", "Unknown") if user else "Unknown",
        "balance": wallet.get("balance", 0),
        "currency": wallet.get("currency", "INR"),
        "status": wallet.get("status", "Unknown"),
    })


# ── Tool 2: Get Recent Transactions ──

@tool
async def get_recent_transactions(user_id: str, limit: int = 10, transaction_type: str = "all") -> str:
    """Get the user's recent transactions.
    Use this when the user asks to see their transactions, payment history, or recent activity.

    Args:
        user_id: The user's ID
        limit: Number of transactions to fetch (default 10, max 50)
        transaction_type: Filter by 'debit', 'credit', or 'all'
    """
    from db import get_wallet_by_user_id, get_transactions_for_wallet

    wallet = await get_wallet_by_user_id(user_id)
    if not wallet:
        return "Wallet not found."

    tx_type = None if transaction_type == "all" else transaction_type
    txns = await get_transactions_for_wallet(wallet["_id"], min(limit, 50), tx_type)

    if not txns:
        return "No transactions found for the given criteria."

    return json.dumps({
        "total_found": len(txns),
        "filter": transaction_type,
        "transactions": txns
    })


# ── Tool 3: Spending Analysis ──

@tool
async def analyze_spending(user_id: str, days: int = 30) -> str:
    """Analyze the user's spending patterns over a period.
    Use this when the user asks about their spending habits, expenses, how much they've spent,
    who they send money to most, or wants a financial summary.

    Args:
        user_id: The user's ID
        days: Number of days to analyze (7, 14, 30, 60, 90)
    """
    from db import get_wallet_by_user_id, get_spending_aggregation

    wallet = await get_wallet_by_user_id(user_id)
    if not wallet:
        return "Wallet not found."

    data = await get_spending_aggregation(wallet["_id"], min(days, 90))
    return json.dumps(data)


# ── Tool 4: Daily Limit Check ──

@tool
async def check_daily_limit(user_id: str) -> str:
    """Check how much of the daily ₹1,00,000 transfer limit the user has consumed.
    Use this when the user asks about their daily limit, remaining limit, or how much more they can send.
    """
    from db import get_wallet_by_user_id, get_daily_limit_usage

    wallet = await get_wallet_by_user_id(user_id)
    if not wallet:
        return "Wallet not found."

    data = await get_daily_limit_usage(wallet["_id"])
    return json.dumps(data)


# ── Tool 5: Transaction Search ──

@tool
async def search_transactions(user_id: str, search_username: str = "", min_amount: float = 0, max_amount: float = 0) -> str:
    """Search transactions by username or amount range.
    Use this when the user wants to find specific transactions, payments to/from a particular person,
    or transactions within a certain amount range.

    Args:
        user_id: The user's ID
        search_username: Username to search for in transaction peers
        min_amount: Minimum transaction amount (0 means no minimum)
        max_amount: Maximum transaction amount (0 means no maximum)
    """
    from db import get_wallet_by_user_id, get_transactions_for_wallet

    wallet = await get_wallet_by_user_id(user_id)
    if not wallet:
        return "Wallet not found."

    all_txns = await get_transactions_for_wallet(wallet["_id"], 50)

    results = []
    for tx in all_txns:
        # Filter by username
        if search_username:
            peer = tx.get("peerUsername", "")
            if search_username.lower() not in peer.lower():
                continue

        # Filter by amount range
        amount = tx.get("amount", 0)
        if min_amount > 0 and amount < min_amount:
            continue
        if max_amount > 0 and amount > max_amount:
            continue

        results.append(tx)

    if not results:
        return f"No transactions found matching your search criteria."

    return json.dumps({
        "total_found": len(results),
        "search_criteria": {
            "username": search_username or "any",
            "min_amount": min_amount,
            "max_amount": max_amount
        },
        "transactions": results[:20]
    })


# ── Tool 6: Account Info ──

@tool
async def get_account_info(user_id: str) -> str:
    """Get the user's account information including username, email, and account status.
    Use this when the user asks about their profile, account details, or personal information.
    """
    from db import get_user_by_id, get_wallet_by_user_id

    user = await get_user_by_id(user_id)
    if not user:
        return "User not found."

    wallet = await get_wallet_by_user_id(user_id)

    return json.dumps({
        "name": user.get("name", ""),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "active": user.get("active", False),
        "created_at": str(user.get("createdAt", "")),
        "wallet_status": wallet.get("status", "Not found") if wallet else "No wallet",
        "wallet_currency": wallet.get("currency", "INR") if wallet else "N/A",
    })


# ── Tool 7: Expense Control Tips ──

@tool
async def get_expense_tips(user_id: str, category: str = "general") -> str:
    """Provide personalized expense control techniques and financial tips based on the user's spending data.
    Use this when the user asks for advice on saving money, reducing expenses, budgeting tips,
    or how to control their spending.

    Args:
        user_id: The user's ID
        category: Tip category — 'general', 'budgeting', 'saving', 'daily_habits'.
                  NOTE: AtomPay does NOT offer investing/SIPs/mutual funds, so there is
                  deliberately no 'investing' category. Never suggest AtomPay investment products.
    """
    from db import get_wallet_by_user_id, get_spending_aggregation, get_daily_limit_usage

    wallet = await get_wallet_by_user_id(user_id)
    spending_data = None
    daily_data = None

    if wallet:
        spending_data = await get_spending_aggregation(wallet["_id"], 30)
        daily_data = await get_daily_limit_usage(wallet["_id"])

    context = {
        "category": category,
        "user_spending_30d": spending_data,
        "daily_usage": daily_data,
        "tips_database": {
            "general": [
                "Follow the 50/30/20 rule: 50% needs, 30% wants, 20% savings",
                "Track every expense for a month to identify spending patterns",
                "Set up automatic transfers to a savings account on payday",
                "Review your subscriptions monthly and cancel unused ones",
                "Use the 24-hour rule: wait before making non-essential purchases over ₹1,000",
            ],
            "budgeting": [
                "Create category-wise monthly budgets (food, transport, entertainment)",
                "Use envelope budgeting: allocate fixed amounts to each category",
                "Track your daily spending against weekly targets",
                "Set realistic budgets based on your last 3 months of spending",
                "Review and adjust your budget every month",
            ],
            "saving": [
                "Save first, spend later — treat savings as a non-negotiable expense",
                "Build an emergency fund covering 6 months of expenses",
                "Use the ₹500 note challenge: save every ₹500 note you receive",
                "Automate your savings with recurring transfers",
                "Set specific savings goals with deadlines (vacation, gadget, etc.)",
            ],
            "daily_habits": [
                "Cook at home more often — eating out can be 3-5x more expensive",
                "Use public transport or carpooling to reduce commute costs",
                "Buy generic/store brands for everyday items",
                "Plan your meals weekly to reduce food waste and impulse buying",
                "Use cashback and rewards programs strategically",
            ],
        }
    }

    return json.dumps(context)


# ── Tool 8: AtomPay Knowledge Base (anti-hallucination grounding) ──

# Authoritative, hand-curated facts about AtomPay. The agent MUST use this as
# the single source of truth for product questions instead of guessing.
ATOMPAY_KNOWLEDGE = {
    "scope": (
        "AtomPay is strictly a digital wallet and peer-to-peer payment app. "
        "Users hold an INR wallet balance and send/receive money to other AtomPay "
        "users by username or QR code."
    ),
    "supported_features": [
        "Wallet balance and wallet status (Active/Frozen)",
        "Sending money to another AtomPay user by @username or QR code",
        "Receiving money via your QR code / username",
        "Transaction history with search and filters",
        "Spending analytics, insights and a daily-limit monitor",
        "AI assistant for budgeting and saving guidance",
    ],
    "unsupported_features": [
        "Investments, mutual funds, SIPs, stocks or trading",
        "Loans, EMIs, overdrafts, credit cards or 'buy now pay later'",
        "Fixed deposits, savings accounts with interest, or insurance",
        "Bill payments, recharges, or merchant card processing",
        "International transfers or currencies other than INR",
    ],
    "limits_and_rules": [
        "Daily transfer limit is Rs 1,00,000 per user (rolling 24 hours).",
        "Per-transaction amount must be between Rs 1 and Rs 1,00,000.",
        "Only INR is supported.",
        "The AI assistant can READ data only — it cannot send money or change the account.",
    ],
    "security": [
        "Login uses email + password + a 6-digit OTP (valid 60 seconds).",
        "Transfers are protected by a PIN.",
        "The assistant never reveals PINs, passwords, OTPs or internal IDs.",
    ],
}


@tool
async def get_atompay_info(topic: str = "all") -> str:
    """Get AUTHORITATIVE facts about what AtomPay is and does. ALWAYS use this
    before answering any question about AtomPay's features, scope, limits, rules,
    or whether something is supported (e.g. SIPs, loans, investments). Never guess
    about the product — only state what this tool returns.

    Args:
        topic: One of 'all', 'scope', 'supported_features', 'unsupported_features',
               'limits_and_rules', 'security'.
    """
    if topic and topic != "all" and topic in ATOMPAY_KNOWLEDGE:
        return json.dumps({topic: ATOMPAY_KNOWLEDGE[topic]})
    return json.dumps(ATOMPAY_KNOWLEDGE)


# ── Tool 9: Month-over-month comparison ──

@tool
async def compare_spending_periods(user_id: str, days: int = 30) -> str:
    """Compare the user's spending in the most recent period against the period
    immediately before it (e.g. this month vs last month). Use this for trends,
    'am I spending more than before', or month-over-month questions.

    Args:
        user_id: The user's ID
        days: Length of each period in days (default 30)
    """
    from db import get_wallet_by_user_id, compare_periods

    wallet = await get_wallet_by_user_id(user_id)
    if not wallet:
        return "Wallet not found."
    return json.dumps(await compare_periods(wallet["_id"], min(max(days, 1), 90)))


# ── Tool 10: Recurring / subscription detection ──

@tool
async def find_recurring_payments(user_id: str, days: int = 90) -> str:
    """Detect payees the user pays repeatedly — likely subscriptions or regular
    transfers — with their cadence (weekly/monthly) and estimated monthly cost.
    Use this when the user asks about subscriptions, recurring payments, or
    where their money regularly goes.

    Args:
        user_id: The user's ID
        days: Lookback window in days (default 90)
    """
    from db import get_wallet_by_user_id, detect_recurring_payments

    wallet = await get_wallet_by_user_id(user_id)
    if not wallet:
        return "Wallet not found."
    return json.dumps(await detect_recurring_payments(wallet["_id"], min(max(days, 30), 180)))


# ── Tool 11: Cashflow forecast ──

@tool
async def forecast_my_cashflow(user_id: str) -> str:
    """Project the user's spending and wallet balance for the rest of the current
    calendar month based on their pace so far. Use this for 'how much will I spend
    this month', 'will I run low', or forecasting questions.
    """
    from db import get_wallet_by_user_id, forecast_cashflow

    wallet = await get_wallet_by_user_id(user_id)
    if not wallet:
        return "Wallet not found."
    return json.dumps(await forecast_cashflow(wallet["_id"]))


# ── Tool 12: Budget status ──

@tool
async def check_budget_status(user_id: str) -> str:
    """Check the user's progress against the monthly spending budget they set.
    Use this when the user asks about their budget, whether they're on track, or
    how much budget is left. If no budget is set, tell them they can set one.
    """
    from db import get_wallet_by_user_id, get_current_month_spend, forecast_cashflow
    import memory

    mem = memory.get_memory(user_id)
    budget = mem.get("monthly_budget")

    wallet = await get_wallet_by_user_id(user_id)
    if not wallet:
        return "Wallet not found."

    spent = await get_current_month_spend(wallet["_id"])
    fc = await forecast_cashflow(wallet["_id"])

    if not budget:
        return json.dumps({
            "budget_set": False,
            "spent_this_month": spent,
            "projected_month_spend": fc["projected_month_spend"],
            "hint": "No monthly budget set. Ask the user if they'd like to set one.",
        })

    return json.dumps({
        "budget_set": True,
        "monthly_budget": budget,
        "spent_this_month": spent,
        "remaining": round(budget - spent, 2),
        "percentage_used": round((spent / budget) * 100, 1) if budget else 0,
        "projected_month_spend": fc["projected_month_spend"],
        "on_track": fc["projected_month_spend"] <= budget,
    })


# ── Tool 13: Remember a fact about the user (short-term memory) ──

@tool
async def remember_about_user(user_id: str, fact: str, preferred_name: str = "") -> str:
    """Save a short, salient fact about the user so you can personalise future
    replies in this session (e.g. "saving for a bike", "prefers Hindi"). Also use
    this to record the name the user wants to be called via preferred_name.
    Keep facts short and non-sensitive. Never store PINs, passwords or OTPs.

    Args:
        user_id: The user's ID
        fact: A short fact to remember (optional if only setting a name)
        preferred_name: The name the user wants to be called (optional)
    """
    import memory

    if preferred_name.strip():
        memory.set_preferred_name(user_id, preferred_name)
    if fact.strip():
        memory.add_note(user_id, fact)
    return json.dumps({"status": "remembered", "memory": memory.get_memory(user_id)})


@tool
async def set_my_budget(user_id: str, monthly_budget: float) -> str:
    """Set the user's monthly spending budget (in INR). Use this when the user
    says they want a budget like "set my monthly budget to 20000".

    Args:
        user_id: The user's ID
        monthly_budget: The monthly budget amount in INR
    """
    import memory
    memory.set_monthly_budget(user_id, monthly_budget)
    return json.dumps({"status": "budget_set", "monthly_budget": monthly_budget})


@tool
async def set_my_savings_goal(user_id: str, label: str, target: float) -> str:
    """Set a savings goal for the user. Use when the user states a goal like
    "I want to save 50000 for a trip".

    Args:
        user_id: The user's ID
        label: Short label for the goal (e.g. "Goa trip")
        target: Target amount in INR
    """
    import memory
    memory.set_savings_goal(user_id, label, target)
    return json.dumps({"status": "goal_set", "label": label, "target": target})


# ── Export all tools ──

ALL_TOOLS = [
    check_balance,
    get_recent_transactions,
    analyze_spending,
    check_daily_limit,
    search_transactions,
    get_account_info,
    get_expense_tips,
    get_atompay_info,
    compare_spending_periods,
    find_recurring_payments,
    forecast_my_cashflow,
    check_budget_status,
    remember_about_user,
    set_my_budget,
    set_my_savings_goal,
]
