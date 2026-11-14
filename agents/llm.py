"""
Thin wrapper around the chat model. Kept in one place so the model name,
temperature, and API key handling are consistent across all four agents,
and so tests can inject a fake LLM without touching agent code.

LLM_BACKEND selects the model (V2_PLAN.md WP6):
  gemini (default)  Google Gemini via langchain_google_genai; GOOGLE_API_KEY,
                    GEMINI_MODEL. Unchanged from v1.
  ollama            a local Ollama server (OLLAMA_HOST, default
                    http://127.0.0.1:11434; OLLAMA_MODEL, required). Uses
                    Ollama's JSON-schema-constrained output through its HTTP
                    API, with the standard library only.

Both return an object with .with_structured_output(schema).invoke(prompt),
which is all the agents use.
"""
import json
import os
import urllib.request

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
BACKENDS = ("gemini", "ollama")


def get_llm(temperature=0.2):
    backend = os.environ.get("LLM_BACKEND", "gemini").strip().lower()
    if backend not in BACKENDS:
        raise RuntimeError(f"LLM_BACKEND must be one of {BACKENDS}, got {backend!r}")
    if backend == "ollama":
        model = os.environ.get("OLLAMA_MODEL")
        if not model:
            raise RuntimeError("LLM_BACKEND=ollama needs OLLAMA_MODEL (e.g. gemma3:270m)")
        return OllamaChat(model, temperature=temperature,
                          host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
    from langchain_google_genai import ChatGoogleGenerativeAI
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your "
            "free Gemini API key from https://aistudio.google.com/apikey"
        )
    return ChatGoogleGenerativeAI(
        model=DEFAULT_MODEL, temperature=temperature, google_api_key=api_key
    )


class OllamaChat:
    """Minimal structured-output client for a local Ollama server."""

    def __init__(self, model, temperature=0.2, host="http://127.0.0.1:11434", timeout=600):
        self.model, self.temperature, self.host, self.timeout = model, temperature, host, timeout
        self.calls = 0

    def with_structured_output(self, schema):
        client = self

        class _Bound:
            def invoke(self, prompt):
                return client.structured(schema, prompt)
        return _Bound()

    def structured(self, schema, prompt):
        body = json.dumps({
            "model": self.model, "stream": False,
            "messages": [{"role": "user", "content": prompt}],
            "format": schema.model_json_schema(),
            "options": {"temperature": self.temperature,
                        # Cap the output so a degenerate generation (e.g. a small model
                        # repeating a list item) fails fast instead of running to the
                        # context limit; a mild repeat penalty discourages loops.
                        "num_predict": int(os.environ.get("OLLAMA_NUM_PREDICT", "1024")),
                        "repeat_penalty": float(os.environ.get("OLLAMA_REPEAT_PENALTY", "1.15"))},
        }).encode("utf-8")
        req = urllib.request.Request(f"{self.host}/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            reply = json.loads(resp.read().decode("utf-8"))
        self.calls += 1
        return schema.model_validate_json(reply["message"]["content"])
