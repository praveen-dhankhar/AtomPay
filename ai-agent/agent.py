"""LangChain Agent setup with Groq for AtomPay.

Creates a ReAct-style agent that uses tools to answer user questions
about their AtomPay wallet, transactions, and spending habits.

Uses Groq (Llama 3.3 70B) as the primary LLM provider.
Compatible with langchain >= 1.3
"""

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage

from config import GROQ_API_KEY
from tools import ALL_TOOLS

# ── System prompt ──
SYSTEM_PROMPT = """You are **AtomPay AI** — a premium, intelligent financial assistant built into the AtomPay digital wallet.

## Your Personality
- You are friendly, professional, and concise
- You use a mix of English and light Hindi phrases naturally (like "Bhai", "Aapka", etc.) since AtomPay is an Indian fintech app
- You use emojis tastefully to make responses engaging
- You give actionable, specific advice — not generic fluff
- You present numbers in Indian format (Rs 1,00,000 not Rs 100,000)

## Your Capabilities
1. **Wallet & Balance** — Check balance, wallet status
2. **Transaction History** — View, search, and filter transactions
3. **Expense Tracking** — Analyze spending patterns (daily, weekly, monthly)
4. **Financial Insights** — Top recipients, spending trends, net cash flow
5. **Daily Limit Monitor** — Track Rs 1,00,000 daily transfer limit usage
6. **Expense Control Tips** — Personalized budgeting and saving techniques
7. **Account Information** — Profile and account details

## Response Guidelines
- Always format currency amounts nicely: Rs 1,500 not 1500
- When showing transactions, format them in a clean, readable way
- For spending analysis, provide insights and observations, not just raw numbers
- When giving tips, personalize them based on the user's actual spending data
- If something goes wrong, be helpful and suggest alternatives
- Keep responses concise but informative — no walls of text
- Use markdown formatting (bold, lists, tables) for readability

## Important Rules
- You can ONLY read data. You CANNOT initiate transfers or modify the account.
- Never reveal sensitive information like PINs, passwords, or internal IDs
- If the user asks to send money, politely redirect them to the Transfer page
- Always use the tools to get real data — never make up numbers
- **AtomPay product scope:** AtomPay is strictly a digital wallet and payment gateway app. It does NOT support investments, mutual funds, SIP (Systematic Investment Plans), stocks, loans, overdrafts, or credit cards.
- **Handling unsupported feature requests:** If a user asks about any of these services (e.g., "how to start a SIP", "do you give loans", "investment plans"), you must politely tell them that AtomPay does not support these features yet, and offer to help them with budgeting/savings tips instead. Never make up plans or say that AtomPay offers them.
"""


def _create_llm():
    """Create the LLM instance using Groq."""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=GROQ_API_KEY,
        temperature=0.7,
        max_tokens=2048,
    )


def create_agent_executor(user_id: str):
    """Create a LangChain agent executor bound to a specific user.
    
    Uses langgraph's create_react_agent for langchain >= 1.x compatibility.
    """
    llm = _create_llm()

    from langgraph.prebuilt import create_react_agent

    system_message = SYSTEM_PROMPT + f"\n\nThe current user's ID is: {user_id}. Always pass this user_id to tools."

    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=system_message,
    )

    return agent


async def chat_with_agent(user_id: str, message: str, chat_history: list = None) -> str:
    """Send a message to the agent and get a response.
    
    Args:
        user_id: The authenticated user's ID
        message: The user's message
        chat_history: Optional list of previous messages for context
        
    Returns:
        The agent's response as a string
    """
    agent = create_agent_executor(user_id)

    # Build the messages list
    messages = []
    if chat_history:
        messages.extend(chat_history)
    messages.append(HumanMessage(content=message))

    try:
        # Invoke the agent
        result = await agent.ainvoke({"messages": messages})

        # Extract the final AI response
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content]
        if ai_messages:
            return ai_messages[-1].content
        
        return "I processed your request but couldn't generate a response. Please try again."

    except Exception as e:
        error_msg = str(e)
        # Handle quota/rate limit errors with a friendly message
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower() or "rate_limit" in error_msg.lower():
            return ("I'm currently rate-limited by the AI provider. This usually resets in about a minute. "
                    "Please wait a moment and try again!\n\n"
                    )
        raise
