"""Configuration loader for the AI Agent microservice."""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")
PORT = int(os.getenv("PORT", 8000))

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is required — get one free at https://console.groq.com/keys")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL is required")
