# Real-LLM environment (WP6)

Recorded 15 Nov 2026 on the machine that ran the WP6 smoke tests.

## Machine

| | |
|---|---|
| RAM | 15.7 GB |
| CPU | 13th Gen Intel Core i7-1355U |
| GPU | Intel Iris Xe Graphics (integrated; no dedicated VRAM; no NVIDIA GPU, `nvidia-smi` not present) |
| OS | Windows 11 (10.0.26200) |

**Model choice rule** (set by the project owner): a GPU with ≥ 8 GB VRAM → `qwen2.5:7b`;
otherwise → `qwen2.5:3b`. There is no dedicated VRAM here, so the model is **`qwen2.5:3b`**.

## Ollama

- **Server version:** 0.40.16 (`GET /api/version`), at `http://127.0.0.1:11434`.
- **Auto-update note:**
  - Ollama was **0.16.2** when this work started.
  - On 15 Nov 2026, an `ollama list` call made during WP6 setup launched the Ollama desktop app.
  - The desktop app's auto-updater downloaded and installed **v0.40.16** (`OllamaSetup.exe`,
    around 01:37 local time). Nobody chose to upgrade.
  - Every WP6 run so far used **0.40.16**.
  - Afterwards the desktop app was not started again. The model was pulled with
    `ollama pull qwen2.5:3b` (CLI) against the already running server.

## Models

| Model | Digest (sha256) | Size | Parameters / quantisation | Pulled |
|---|---|---|---|---|
| `qwen2.5:3b` | `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` | 1,929,912,432 B | 3.1B, Q4_K_M | 15 Nov 2026 03:51 (CLI pull; Ollama verified the digest) |
| `gemma3:270m` | `e7d36fb2c3b3293cfe56d55889867a064b3a2b22e98335f2e6e8a387e081d6be` | 291,554,930 B | 268M, Q8_0 | present before this work; used for the first smoke test only (too small; see that run's report) |

## Client settings (agents/llm.py, LLM_BACKEND=ollama)

| Setting | Value |
|---|---|
| Temperature | 0.2 |
| Output format | JSON-schema-constrained via Ollama's `format` |
| `OLLAMA_NUM_PREDICT` | 1024 (default) |
| `OLLAMA_REPEAT_PENALTY` | 1.15 (default) |
