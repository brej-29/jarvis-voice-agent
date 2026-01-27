# Backend Deployment (FastAPI + Local LLM)

This document explains how to build and run the backend in different environments,
including local development with Ollama and container-based deployments such as
Hugging Face Docker Spaces.

For a **complete, free-first deployment runbook**, see:

- `context/RUN_LOCAL.md` – local dev (backend + mobile).
- `context/DEPLOY_FREE.md` – free deployment paths (HF Spaces + Cloudflare tunnel).

## 1. Local Development (Recommended)

Prerequisites:

- Python 3.11
- Ollama installed and running locally (for LLM inference)

Steps:

```bash
cd backend

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` if needed, for example:

- `LLM_PROVIDER=ollama` (default, local-first)
- `OLLAMA_MODEL=mistral`
- `OLLAMA_BASE_URL=http://localhost:11434`

Run the app:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

The `/chat` endpoint is documented in `context/API_CONTRACT.md`.

> Note: For local use, the backend expects Ollama at `http://localhost:11434`.
> You can override this via `OLLAMA_BASE_URL` in `.env`.

## 2. Docker Image

The `backend/Dockerfile` builds a containerized version of the FastAPI backend.

Build:

```bash
cd backend
docker build -t jarvis-backend .
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -e PORT=8000 \
  -e APP_ENV=local \
  jarvis-backend
```

The container:

- Exposes the port via `$PORT` (default 8000).
- Starts the app with:

  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

### Ollama Considerations in Docker

The Docker image does **not** bundle Ollama or any model. Typical options:

- Run Ollama on the host and connect the container to it via
  `OLLAMA_BASE_URL=http://host.docker.internal:11434` (on macOS/Windows).
- Or run Ollama in a separate container and connect via Docker networking.

In both cases, keep it **local-only** by default to preserve the free-first and
privacy-friendly architecture.

## 3. Hugging Face Docker Spaces

Hugging Face Spaces can run arbitrary Docker containers. To use this backend:

1. Point the Space to the `backend/` directory and use `Dockerfile` as the build file.

2. HF Spaces will set a `$PORT` environment variable which the app must bind to.
   The provided Dockerfile and entrypoint already respect this.

3. Constraints:

   - HF CPU-only Spaces cannot run Ollama with GPU acceleration.
   - Running Ollama inside the same container is typically not feasible due to
     resource and environment constraints.
   - As a result, this backend should be configured to use the **LlamaCpp** provider
     for demos:

     - Set `LLM_PROVIDER=llamacpp`.
     - Optionally override:
       - `LLAMACPP_MODEL_REPO`
       - `LLAMACPP_MODEL_FILE`
       - `LLAMACPP_CONTEXT_LENGTH`
       - `LLAMACPP_MAX_TOKENS`

     See `context/DEPLOY_FREE.md` for a detailed HF Spaces step-by-step guide.

4. If you deploy the backend on HF and the TinyLlama model cannot be downloaded or
   initialized, the `/chat` endpoint will fall back to friendly “demo degraded”
   messages instead of returning 500 errors.

In keeping with the **free-first** constraint, this repository does not include
paid SaaS integrations. Any cloud-based LLM usage should be opt-in and configured
explicitly via environment variables, outside the default flow.