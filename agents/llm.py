"""
Thin wrapper around the Gemini chat model. Kept in one place so the
model name, temperature, and API key handling are consistent across all
four agents, and so tests can inject a fake LLM without touching agent
code.
"""
import os
from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def get_llm(temperature=0.2):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your "
            "free Gemini API key from https://aistudio.google.com/apikey"
        )
    return ChatGoogleGenerativeAI(
        model=DEFAULT_MODEL, temperature=temperature, google_api_key=api_key
    )
