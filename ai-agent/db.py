"""Async MongoDB connection for the AI Agent.

Connects to the same AtomPay MongoDB database used by the Node.js backend.
Uses Motor (async pymongo driver) for non-blocking reads.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

_client: AsyncIOMotorClient | None = None
_db = None


async def get_db():
    """Get a reference to the AtomPay database."""
    global _client, _db
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URL)
        # Extract DB name from the connection string (after last '/')
        db_name = MONGO_URL.rstrip("/").split("/")[-1].split("?")[0]
        _db = _client[db_name]
    return _db


async def close_db():
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


# ── Helper functions for the LangChain tools ──

async def get_user_by_id(user_id: str) -> dict | None:
    """Fetch user document by _id."""
    from bson import ObjectId
    db = await get_db()
    return await db.users.find_one({"_id": ObjectId(user_id)})


async def get_wallet_by_user_id(user_id: str) -> dict | None:
    """Fetch wallet document for a user."""
    from bson import ObjectId
    db = await get_db()
    return await db.wallets.find_one({"user": ObjectId(user_id)})


async def get_transactions_for_wallet(wallet_id, limit: int = 50, tx_type: str = None) -> list:
    """Fetch transactions for a wallet, optionally filtered by type (debit/credit)."""
    from bson import ObjectId
    db = await get_db()

    query = {
        "$or": [
            {"fromWallet": wallet_id},
            {"toWallet": wallet_id}
        ]
    }

    cursor = db.transactions.find(query).sort("createdAt", -1).limit(limit)
    txns = []
    async for tx in cursor:
        is_debit = str(tx.get("fromWallet")) == str(wallet_id)
        tx_entry = {
            "transactionId": tx.get("transactionId", ""),
            "amount": tx.get("amount", 0),
            "status": tx.get("status", ""),
            "type": "debit" if is_debit else "credit",
            "note": tx.get("note", ""),
            "senderUsername": tx.get("senderUsername", ""),
            "receiverUsername": tx.get("receiverUsername", ""),
            "peerUsername": tx.get("receiverUsername") if is_debit else tx.get("senderUsername"),
            "createdAt": str(tx.get("createdAt", "")),
        }
        if tx_type and tx_entry["type"] != tx_type:
            continue
        txns.append(tx_entry)
    return txns


async def get_spending_aggregation(wallet_id, days: int = 30) -> dict:
    """Aggregate spending data for the last N days."""
    from bson import ObjectId
    from datetime import datetime, timedelta
    db = await get_db()

    since = datetime.utcnow() - timedelta(days=days)

    # Total sent (debits)
    pipeline_sent = [
        {"$match": {"fromWallet": wallet_id, "status": "success", "createdAt": {"$gte": since}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]

    # Total received (credits)
    pipeline_received = [
        {"$match": {"toWallet": wallet_id, "status": "success", "createdAt": {"$gte": since}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]

    # Top recipients
    pipeline_top = [
        {"$match": {"fromWallet": wallet_id, "status": "success", "createdAt": {"$gte": since}}},
        {"$group": {"_id": "$receiverUsername", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": 5},
    ]

    # Daily breakdown
    pipeline_daily = [
        {"$match": {"fromWallet": wallet_id, "status": "success", "createdAt": {"$gte": since}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": -1}},
    ]

    sent_result = await db.transactions.aggregate(pipeline_sent).to_list(1)
    received_result = await db.transactions.aggregate(pipeline_received).to_list(1)
    top_recipients = await db.transactions.aggregate(pipeline_top).to_list(5)
    daily_breakdown = await db.transactions.aggregate(pipeline_daily).to_list(60)

    return {
        "period_days": days,
        "total_sent": sent_result[0]["total"] if sent_result else 0,
        "sent_count": sent_result[0]["count"] if sent_result else 0,
        "total_received": received_result[0]["total"] if received_result else 0,
        "received_count": received_result[0]["count"] if received_result else 0,
        "net_flow": (received_result[0]["total"] if received_result else 0) - (sent_result[0]["total"] if sent_result else 0),
        "top_recipients": [{"username": r["_id"], "amount": r["total"], "count": r["count"]} for r in top_recipients],
        "daily_breakdown": [{"date": d["_id"], "amount": d["total"], "count": d["count"]} for d in daily_breakdown],
    }


async def get_daily_limit_usage(wallet_id) -> dict:
    """Check how much of the ₹1,00,000 daily limit has been used."""
    from datetime import datetime, timedelta
    db = await get_db()

    since = datetime.utcnow() - timedelta(hours=24)
    pipeline = [
        {"$match": {"fromWallet": wallet_id, "status": "success", "createdAt": {"$gte": since}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    result = await db.transactions.aggregate(pipeline).to_list(1)
    used = result[0]["total"] if result else 0
    return {
        "daily_limit": 100000,
        "used": used,
        "remaining": max(0, 100000 - used),
        "percentage_used": round((used / 100000) * 100, 1),
        "transaction_count_today": result[0]["count"] if result else 0,
    }


# ── Analytics helpers (deterministic, no LLM) ──

async def _window_totals(wallet_id, start, end) -> dict:
    """Sum of successful sent/received amounts in [start, end)."""
    db = await get_db()

    async def _sum(direction):
        field = "fromWallet" if direction == "sent" else "toWallet"
        pipeline = [
            {"$match": {field: wallet_id, "status": "success",
                        "createdAt": {"$gte": start, "$lt": end}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        ]
        res = await db.transactions.aggregate(pipeline).to_list(1)
        return (res[0]["total"], res[0]["count"]) if res else (0, 0)

    sent, sent_count = await _sum("sent")
    received, received_count = await _sum("received")
    return {
        "total_sent": sent,
        "sent_count": sent_count,
        "total_received": received,
        "received_count": received_count,
        "net_flow": received - sent,
    }


def _pct_change(current, previous) -> float | None:
    """Percentage change from previous to current; None if previous is 0."""
    if not previous:
        return None
    return round(((current - previous) / previous) * 100, 1)


async def compare_periods(wallet_id, days: int = 30) -> dict:
    """Compare the most recent `days` window with the one immediately before it."""
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    cur_start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)

    current = await _window_totals(wallet_id, cur_start, now)
    previous = await _window_totals(wallet_id, prev_start, cur_start)

    return {
        "period_days": days,
        "current": current,
        "previous": previous,
        "change": {
            "sent_pct": _pct_change(current["total_sent"], previous["total_sent"]),
            "received_pct": _pct_change(current["total_received"], previous["total_received"]),
            "net_pct": _pct_change(current["net_flow"], previous["net_flow"]),
            "sent_delta": current["total_sent"] - previous["total_sent"],
            "received_delta": current["total_received"] - previous["total_received"],
        },
    }


async def detect_recurring_payments(wallet_id, days: int = 90, min_count: int = 3) -> dict:
    """Find payees the user pays repeatedly — likely subscriptions/regular transfers.

    A payee is flagged when there are >= min_count successful debits to them in
    the window. Cadence (avg days between payments) hints at the billing cycle.
    """
    from datetime import datetime, timedelta
    db = await get_db()

    since = datetime.utcnow() - timedelta(days=days)
    pipeline = [
        {"$match": {"fromWallet": wallet_id, "status": "success", "createdAt": {"$gte": since}}},
        {"$group": {
            "_id": "$receiverUsername",
            "count": {"$sum": 1},
            "total": {"$sum": "$amount"},
            "avg_amount": {"$avg": "$amount"},
            "dates": {"$push": "$createdAt"},
        }},
        {"$match": {"count": {"$gte": min_count}}},
        {"$sort": {"total": -1}},
        {"$limit": 20},
    ]
    rows = await db.transactions.aggregate(pipeline).to_list(20)

    def _cadence(dates):
        ds = sorted(dates)
        if len(ds) < 2:
            return None
        gaps = [(ds[i] - ds[i - 1]).total_seconds() / 86400 for i in range(1, len(ds))]
        return round(sum(gaps) / len(gaps), 1)

    def _label(cadence):
        if cadence is None:
            return "irregular"
        if 25 <= cadence <= 35:
            return "monthly"
        if 6 <= cadence <= 8:
            return "weekly"
        if 13 <= cadence <= 16:
            return "fortnightly"
        if cadence < 6:
            return "frequent"
        return "periodic"

    recurring = []
    for r in rows:
        cadence = _cadence(r["dates"])
        recurring.append({
            "username": r["_id"],
            "count": r["count"],
            "total": r["total"],
            "avg_amount": round(r["avg_amount"], 2),
            "cadence_days": cadence,
            "cadence_label": _label(cadence),
        })

    est_monthly = round(
        sum(r["avg_amount"] for r in recurring if r["cadence_label"] in ("monthly", "periodic", "fortnightly", "weekly")), 2
    )
    return {
        "window_days": days,
        "recurring_count": len(recurring),
        "estimated_monthly_recurring": est_monthly,
        "recurring": recurring,
    }


async def forecast_cashflow(wallet_id) -> dict:
    """Project this calendar month's spend and month-end balance from the pace so far."""
    from datetime import datetime
    import calendar

    db = await get_db()
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_elapsed = max(1, (now - month_start).days + 1)
    days_remaining = max(0, days_in_month - days_elapsed)

    totals = await _window_totals(wallet_id, month_start, now)
    spent = totals["total_sent"]
    received = totals["total_received"]

    avg_daily_spend = spent / days_elapsed
    avg_daily_received = received / days_elapsed
    projected_spend = round(avg_daily_spend * days_in_month, 2)
    projected_received = round(avg_daily_received * days_in_month, 2)

    wallet = await db.wallets.find_one({"_id": wallet_id})
    current_balance = wallet.get("balance", 0) if wallet else 0
    projected_balance = round(
        current_balance + (avg_daily_received - avg_daily_spend) * days_remaining, 2
    )

    return {
        "month": now.strftime("%B %Y"),
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "spent_so_far": spent,
        "received_so_far": received,
        "avg_daily_spend": round(avg_daily_spend, 2),
        "projected_month_spend": projected_spend,
        "projected_month_received": projected_received,
        "current_balance": current_balance,
        "projected_month_end_balance": projected_balance,
    }


async def get_current_month_spend(wallet_id) -> int:
    """Total successful debits in the current calendar month (for budget tracking)."""
    from datetime import datetime
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    totals = await _window_totals(wallet_id, month_start, now)
    return totals["total_sent"]
