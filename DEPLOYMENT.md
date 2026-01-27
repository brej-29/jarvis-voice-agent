# Deployment Guide

This document outlines practical ways to deploy and run the Jarvis Voice Agent
backend while keeping to the **free-first**, **local-first** constraints.

---

## Option A: Local Backend + Local Ollama (Recommended)

In this setup:

- Ollama runs on your laptop/desktop.
- The FastAPI backend runs on the same machine.
- Your phone/emulator connects to the backend over the local network.

### Steps

1. **Run Ollama locally**

   - Install Ollama: https://ollama.ai
   - Pull the model (default: `mistral`):

     ```bash
     ollama pull mistral
     ```

   - Start the Ollama server:

     ```bash
     ollama serve
     ```

   - By default, Ollama listens on `http://localhost:11434`.

2. **Run the backend**

   From the repo root:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

   pip install -r requirements.txt
   cp .env.example .env
   ```

   Adjust `.env` if needed (e.g., different `OLLAMA_MODEL`).

   Start the API:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   Health check:

   ```bash
   curl http://localhost:8000/health
   ```

3. **Connect the mobile app**

   - For Android emulator:
     - Use `http://10.0.2.2:8000` (already the default in `Config`).
   - For iOS simulator or desktop:
     - Use `http://localhost:8000`.

   On a physical device:

   - Ensure your phone is on the same Wi-Fi network as the backend machine.
   - Find your machine’s local IP (e.g., `192.168.1.10`).
   - Set the backend base URL from the app Settings:

     ```text
     http://192.168.1.10:8000
     ```

---

## Option B: Dockerized Backend (Local or Remote)

You can run the backend in a Docker container using `backend/Dockerfile`.

### Local Docker

From the repo root:

```bash
cd backend
docker build -t jarvis-backend .
docker run --rm -p 8000:8000 \
  -e PORT=8000 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  jarvis-backend
```

Notes:

- `host.docker.internal` lets the container talk to Ollama running on the host
  (macOS/Windows). On Linux, you may need to use the host IP or Docker’s bridge IP.
- All configuration is driven via environment variables; see `backend/.env.example`
  for details.

The mobile app connects exactly as in Option A (using your host’s IP).

### Hugging Face Docker Spaces (Backend Only)

You can deploy **just the backend** to a Hugging Face Docker Space:

1. Configure the Space to build from `backend/Dockerfile`.
2. HF sets `$PORT` automatically; the Dockerfile and uvicorn command respect it.
3. Expose the `/health` and `/chat` endpoints on that port.

**Important limitation:**

- HF CPU Spaces are not suitable for running Ollama with local models.
- This backend assumes a reachable Ollama instance. In HF, you would typically:
  - Point `OLLAMA_BASE_URL` to a remote Ollama instance you control, or
  - Swap in a different (free) LLM backend via future configuration.

If Ollama is unreachable, `/chat` will:

- Log the error server-side.
- Return a friendly message to the client explaining the local LLM is unavailable.

This keeps behavior predictable even when deployed in environments without Ollama.

---

## Security & Network Considerations

- This V1 is designed for **trusted, local environments**:
  - No authentication on `/chat`.
  - CORS is open for local development by default.
- For any remote deployment:
  - Restrict allowed origins via `CORS_ALLOW_ORIGINS`.
  - Place the backend behind a reverse proxy or VPN.
  - Add authentication (API keys, tokens) before exposing publicly.

---

## Summary

- **Local laptop + phone on same Wi-Fi** is the primary target deployment.
- Docker support allows you to:
  - Run the backend in a container locally.
  - Experiment with remote backends (e.g., HF Spaces) while still keeping a
    free-first, local LLM philosophy.
- The system is intentionally simple in V1 so we can iterate on features
  (tool routing, NLU, persistence) without being blocked by infrastructure complexity.