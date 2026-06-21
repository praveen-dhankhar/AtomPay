"""LangChain Agent setup with DeepSeek for AtomPay.

Creates a ReAct-style agent that uses tools to answer user questions
about their AtomPay wallet, transactions, and spending habits.

Uses DeepSeek (deepseek-chat / V3) as the LLM provider. Hallucinations are
controlled WITHOUT a RAG/vector store, via three layers:
  1. Strict tool-grounding — every fact comes from a tool, never invented.
  2. An authoritative AtomPay knowledge tool for product questions.
  3. A model self-verification pass that re-checks the draft answer against the
     data the tools actually returned, and corrects unsupported claims.

Compatible with langchain >= 0.3
"""

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

import memory
from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    VERIFY_RESPONSES,
    is_llm_configured,
)
from tools import ALL_TOOLS

# ── System prompt ──
SYSTEM_PROMPT = """You are **AtomAI** — a premium, intelligent financial assistant built into the AtomPay digital wallet. Your name is AtomAI; always refer to yourself as AtomAI, never as "AtomPay AI" or "AI Agent".

## Your Personality
- You are friendly, professional, and concise
- You communicate ONLY in clear, professional English. Do NOT use Hindi or Hinglish words or slang (no "Bhai", "Aapka", "Paisa", etc.) — keep it polished and professional at all times
- You use emojis tastefully to make responses engaging
- You give actionable, specific advice — not generic fluff
- You present amounts in the Indian numbering format (Rs 1,00,000 not Rs 100,000), but always write in English
- Address the user by their first name when it feels natural and warm

## Your Capabilities
1. **Wallet & Balance** — Check balance, wallet status
2. **Transaction History** — View, search, and filter transactions
3. **Expense Tracking** — Analyze spending patterns (daily, weekly, monthly)
4. **Financial Insights** — Top recipients, spending trends, net cash flow
5. **Month-over-month trends** — Compare this period vs the previous one
6. **Recurring payments** — Detect subscriptions and regular transfers
7. **Budget & savings goals** — Track a budget the user sets and savings goals
8. **Cashflow forecast** — Project month-end spend and balance
9. **Daily Limit Monitor** — Track Rs 1,00,000 daily transfer limit usage
10. **Expense Control Tips** — Personalized budgeting and saving techniques

## ANTI-HALLUCINATION RULES (most important)
- You MUST base every factual or numeric claim on data returned by a tool in THIS turn. Never invent, estimate, or recall numbers from earlier guesses.
- If a tool returns no data or an error, say so plainly — do NOT fabricate a plausible-looking answer.
- For ANY question about what AtomPay is, what it supports, its limits or rules, you MUST call `get_atompay_info` and answer ONLY from its result.
- If you are unsure or lack a tool to answer, say you don't have that information rather than guessing.
- Never reveal sensitive information like PINs, passwords, OTPs, or internal IDs.
- You can ONLY read data. You CANNOT initiate transfers or modify the account. If the user asks to send money, redirect them to the Transfer page.

## AtomPay product scope (AUTHORITATIVE — this is the ground truth, never contradict it)
AtomPay is STRICTLY a digital wallet and peer-to-peer payment app for INR only.

SUPPORTED:
- Wallet balance and status (Active/Frozen)
- Sending/receiving money to other AtomPay users by @username or QR code
- Transaction history with search and filters
- Spending analytics, insights, and a daily-limit monitor
- AI assistant for budgeting and saving guidance

NOT SUPPORTED — you must NEVER claim AtomPay offers any of these:
- Investments, mutual funds, SIPs, stocks, or trading
- Loans, EMIs, overdrafts, credit cards, or "buy now pay later"
- Fixed deposits, interest-bearing savings accounts, or insurance
- Bill payments, recharges, or merchant card processing
- International transfers or any currency other than INR

If the user asks whether AtomPay supports any unsupported item, clearly state that AtomPay does NOT support it, then offer budgeting/savings help instead. You may call `get_atompay_info` to confirm, but the lists above are authoritative — never invent or imply a feature that is not listed as SUPPORTED.

## Memory
- You have short-term memory of this user (shown below). Use it to personalise replies.
- When the user shares something worth remembering (a goal, a preference, the name they like), call `remember_about_user`. When they set a budget or savings goal, call `set_my_budget` / `set_my_savings_goal`.

## Response Guidelines
- Always format currency nicely: Rs 1,500 not 1500
- Present transactions and analytics in clean, readable markdown (bold, lists, small tables)
- For analysis, give insights and observations, not just raw numbers
- Personalize tips using the user's actual data
- Keep responses concise but informative — no walls of text
"""


def _create_llm(temperature: float = 0.1):
    """Create the DeepSeek LLM instance."""
    return ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        api_base=DEEPSEEK_BASE_URL,
        temperature=temperature,
        max_tokens=2048,
    )


def _build_system_message(user_id: str, user_name: str = "") -> str:
    """Assemble the system prompt with per-user context and memory."""
    name_line = f"\nThe user's name is: {user_name}." if user_name else ""
    mem_line = f"\n\n## What you remember about this user\n{memory.memory_summary(user_id)}"
    return (
        SYSTEM_PROMPT
        + name_line
        + f"\nThe current user's ID is: {user_id}. Always pass this user_id to tools."
        + mem_line
    )


def create_agent_executor(user_id: str, user_name: str = ""):
    """Create a LangChain agent executor bound to a specific user."""
    from langgraph.prebuilt import create_react_agent

    llm = _create_llm()
    system_message = _build_system_message(user_id, user_name)

    return create_react_agent(model=llm, tools=ALL_TOOLS, prompt=system_message)


def _collect_tool_data(messages: list) -> str:
    """Concatenate the raw outputs of every tool call in this turn — the only
    facts the answer is allowed to rely on."""
    chunks = []
    for m in messages:
        if isinstance(m, ToolMessage) and m.content:
            name = getattr(m, "name", "tool")
            chunks.append(f"[{name}] {m.content}")
    return "\n".join(chunks)


async def _verify_answer(question: str, tool_data: str, draft: str) -> str:
    """Second-pass check: ensure the draft only states facts present in tool_data.

    If everything checks out, the draft is returned unchanged. Otherwise the
    answer is rewritten to drop or correct unsupported claims. Falls back to the
    draft if the verifier itself errors out.
    """
    import json
    from tools import ATOMPAY_KNOWLEDGE

    # Authoritative product facts are ALWAYS allowed grounding, even when no tool
    # ran this turn — this is what stops the model inventing product features
    # (SIPs, loans, credit cards) on questions that don't trigger a DB tool.
    product_facts = json.dumps(ATOMPAY_KNOWLEDGE)
    has_account_data = bool(tool_data.strip())

    verifier = _create_llm(temperature=0.0)
    instruction = (
        "You are a strict fact-checker for a fintech assistant. You are given the "
        "user's QUESTION, the authoritative PRODUCT_FACTS about what AtomPay does and "
        "does not support, the account DATA that backend tools returned this turn, and a "
        "DRAFT answer.\n\n"
        "Check every factual claim in the DRAFT. Rules:\n"
        "- Any claim about AtomPay's features or scope MUST agree with PRODUCT_FACTS. If "
        "the DRAFT says or implies AtomPay supports something listed as unsupported "
        "(investments, SIPs, stocks, loans, EMIs, credit cards, insurance, bill payments, "
        "international transfers, etc.), correct it to clearly state AtomPay does NOT "
        "support it.\n"
        "- Any account-specific number, name, or date (balance, spending totals, "
        "transactions, limit usage) is allowed ONLY if present in DATA. Remove or correct "
        "anything not in DATA.\n"
        "- Do NOT add new facts. Keep the helpful tone, formatting, and any general "
        "(non-account, non-product) financial advice.\n"
        "- Reply ONLY in clear, professional English — no Hindi or Hinglish words.\n"
        "- If the DRAFT is fully supported, return it unchanged.\n"
        "Return ONLY the final answer text, with no preamble or explanation.\n\n"
        f"QUESTION:\n{question}\n\nPRODUCT_FACTS:\n{product_facts}\n\n"
        f"DATA:\n{tool_data if has_account_data else '(no account tools were called this turn)'}\n\n"
        f"DRAFT:\n{draft}"
    )
    try:
        result = await verifier.ainvoke([
            SystemMessage(content="You correct hallucinations in financial answers."),
            HumanMessage(content=instruction),
        ])
        corrected = (result.content or "").strip()
        return corrected or draft
    except Exception:
        return draft


async def chat_with_agent(user_id: str, message: str, chat_history: list = None,
                          user_name: str = "") -> str:
    """Send a message to the agent and get a verified response."""
    if not is_llm_configured():
        return ("🔧 The AI assistant isn't configured yet — a DeepSeek API key needs "
                "to be added (DEEPSEEK_API_KEY in the ai-agent .env). Once it's set, "
                "I'll be ready to help with your wallet and spending!")

    agent = create_agent_executor(user_id, user_name)

    messages = []
    if chat_history:
        messages.extend(chat_history)
    messages.append(HumanMessage(content=message))

    try:
        result = await agent.ainvoke({"messages": messages})

        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content]
        if not ai_messages:
            return "I processed your request but couldn't generate a response. Please try again."

        draft = ai_messages[-1].content

        if VERIFY_RESPONSES:
            tool_data = _collect_tool_data(result["messages"])
            return await _verify_answer(message, tool_data, draft)

        return draft

    except Exception as e:
        error_msg = str(e)
        if any(k in error_msg.lower() for k in ("429", "rate_limit", "rate limit", "quota", "resource_exhausted")):
            return ("I'm currently rate-limited by the AI provider. This usually resets in about a minute. "
                    "Please wait a moment and try again!")
        if any(k in error_msg.lower() for k in ("401", "authentication", "invalid api key", "api_key")):
            return ("⚠️ The AI provider rejected the API key. Please check that DEEPSEEK_API_KEY "
                    "is set correctly in the ai-agent .env file.")
        raise
