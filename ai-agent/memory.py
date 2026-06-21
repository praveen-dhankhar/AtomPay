"""In-memory short-term memory about each user.

Holds lightweight, per-user context that makes the assistant feel personal
across a session — the user's preferred name, salient facts it has been told
("I'm saving for a bike"), and budget/savings goals.

This is intentionally NOT persisted: it lives in the FastAPI process and is
cleared on restart (and via /memory/clear). It is process-local, so run a
single worker for consistent behaviour.
"""

from __future__ import annotations

import threading
from collections import defaultdict

_LOCK = threading.Lock()

# user_id -> memory dict
_MEMORY: dict[str, dict] = defaultdict(lambda: {
    "preferred_name": None,   # what the user likes to be called
    "notes": [],              # list[str] of salient facts, most-recent last
    "monthly_budget": None,   # float: self-set monthly spending budget (INR)
    "savings_goal": None,     # {"label": str, "target": float} or None
})

MAX_NOTES = 15


def get_memory(user_id: str) -> dict:
    """Return a copy of the user's current memory."""
    with _LOCK:
        m = _MEMORY[user_id]
        return {
            "preferred_name": m["preferred_name"],
            "notes": list(m["notes"]),
            "monthly_budget": m["monthly_budget"],
            "savings_goal": dict(m["savings_goal"]) if m["savings_goal"] else None,
        }


def add_note(user_id: str, note: str) -> None:
    """Remember a salient fact about the user (deduplicated, capped)."""
    note = (note or "").strip()
    if not note:
        return
    with _LOCK:
        notes = _MEMORY[user_id]["notes"]
        if note not in notes:
            notes.append(note)
        if len(notes) > MAX_NOTES:
            del notes[: len(notes) - MAX_NOTES]


def set_preferred_name(user_id: str, name: str) -> None:
    name = (name or "").strip()
    if name:
        with _LOCK:
            _MEMORY[user_id]["preferred_name"] = name


def set_monthly_budget(user_id: str, amount: float) -> None:
    with _LOCK:
        _MEMORY[user_id]["monthly_budget"] = float(amount) if amount and amount > 0 else None


def set_savings_goal(user_id: str, label: str, target: float) -> None:
    with _LOCK:
        if target and target > 0:
            _MEMORY[user_id]["savings_goal"] = {"label": (label or "Savings goal").strip(), "target": float(target)}
        else:
            _MEMORY[user_id]["savings_goal"] = None


def clear_memory(user_id: str) -> None:
    with _LOCK:
        _MEMORY.pop(user_id, None)


def memory_summary(user_id: str) -> str:
    """A compact natural-language summary for injecting into the system prompt."""
    m = get_memory(user_id)
    parts = []
    if m["preferred_name"]:
        parts.append(f'Likes to be called "{m["preferred_name"]}".')
    if m["monthly_budget"]:
        parts.append(f"Has set a monthly spending budget of Rs {int(m['monthly_budget']):,}.")
    if m["savings_goal"]:
        g = m["savings_goal"]
        parts.append(f"Savings goal: {g['label']} (target Rs {int(g['target']):,}).")
    for note in m["notes"]:
        parts.append(note)
    if not parts:
        return "Nothing remembered about this user yet."
    return " ".join(f"- {p}" for p in parts)
