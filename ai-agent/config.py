"""Configuration loader for the AI Agent microservice."""

import os
from dotenv import load_dotenv

load_dotenv()

# ── DeepSeek (primary LLM provider) ──
# Leave DEEPSEEK_API_KEY empty in .env for now — fill it in later.
# The service still boots without it; chat calls will fail gracefully until set.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
# deepseek-chat (V3) supports function/tool calling, which the agent requires.
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Toggle the model self-verification pass that re-checks answers against tool
# data to suppress hallucinations. Costs one extra LLM call per chat turn.
VERIFY_RESPONSES = os.getenv("VERIFY_RESPONSES", "true").lower() != "false"

MONGO_URL = os.getenv("MONGO_URL")
PORT = int(os.getenv("PORT", 8000))

if not MONGO_URL:
    raise RuntimeError("MONGO_URL is required")

if not DEEPSEEK_API_KEY:
    # Don't hard-fail — allow the service to start so the rest of the app keeps
    # working. Chat requests will return a friendly "not configured" message.
    print("[!] DEEPSEEK_API_KEY is empty — set it in .env to enable AI chat. "
          "Get one at https://platform.deepseek.com/api_keys")


def is_llm_configured() -> bool:
    """True when a DeepSeek API key is present."""
    return bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY.strip())
