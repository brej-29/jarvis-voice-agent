# Free Deployment Runbook

This document describes **two fully free deployment paths** for the backend, plus a **free Android distribution path** for the mobile app.

- **Path 1 – Hugging Face Spaces (Docker + CPU LlamaCpp)**  
  Public demo backend using a tiny GGUF model (no Ollama, no paid APIs).
- **Path 2 – Best “Jarvis Experience” (Local backend + Cloudflare Tunnel)**  
  Keep Ollama + backend on your machine, expose it securely via Cloudflare.
- **Mobile distribution – Free Android APK via GitHub Releases**

Both paths respect the project’s **free-first, local-first** philosophy.

---

## Path 1 – Public Backend (Free) via Hugging Face Spaces (Docker)

### 1. How Hugging Face Spaces Works (Constraints)

- HF **Docker Spaces** run your container on **CPU-only** hardware.
- You cannot rely on a local **Ollama** instance:
  - No GPU.
  - No long-lived background daemon like `ollama serve` running on the same host as a normal desktop.
- To keep a **free** public demo:
  - We introduce an alternate LLM provider: **LlamaCpp**.
  - It runs a **small GGUF model** inside the container using `llama-cpp-python`.
  - Model weights are downloaded from **Hugging Face Hub** at startup and cached on disk.

---

### 2. LLM Provider Switch (`LLM_PROVIDER`)

The backend now supports two LLM providers via an environment variable:

- `LLM_PROVIDER=ollama` (default; best for local dev)
  - Uses the existing **Ollama** REST API at `OLLAMA_BASE_URL`.
- `LLM_PROVIDER=llamacpp`
  - Uses a **CPU-only LlamaCpp** client with a tiny GGUF model.
  - Designed specifically for HF Spaces and other CPU‑only environments.

Additional environment variables for the LlamaCpp mode:

- `LLAMACPP_MODEL_REPO`
  - Default: `TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF`
- `LLAMACPP_MODEL_FILE`
  - Default: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`
- `LLAMACPP_CONTEXT_LENGTH`
  - Default: `2048`
- `LLAMACPP_MAX_TOKENS`
  - Default: `256`

These are exposed in `backend/.env.example` and validated by `backend/app/core/config.py`.

---

### 3. LlamaCpp Provider (`backend/app/services/llamacpp_client.py`)

The LlamaCpp provider:

- Uses **`huggingface_hub.hf_hub_download`** to fetch the GGUF model from:
  - Repo: `TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF`
  - File: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` (Q4_K_M quantization)
- Loads the model via **`llama-cpp-python`** (`llama_cpp.Llama`).
- Keeps the **context window** moderate (`2048`) for CPU-friendly performance.
- Logs a clear **“model ready”** message once initialization completes.
- If model download or initialization fails:
  - Logs the exception (with request ID when possible).
  - `/chat` returns a **friendly “demo degraded” message** indicating the demo model is unavailable.
  - No stack traces or internal details are exposed to clients.

The provider is only **activated** if `LLM_PROVIDER=llamacpp`. In all other cases, the system uses the existing **Ollama** client.

---

### 4. Dockerfile Behavior for HF Spaces

`backend/Dockerfile` is HF Spaces–compatible:

- It expects a `PORT` environment variable (default `8000`):

  ```dockerfile
  ENV PORT=8000
  EXPOSE ${PORT}
  CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
  ```

- Hugging Face Spaces typically sets `PORT=7860` for Docker apps.
- The Dockerfile **already honors** whatever `PORT` HF provides, so no changes are required to map `7860`.

When the Space runs:

- The backend listens on `0.0.0.0:${PORT}` (e.g., `0.0.0.0:7860`).
- HF exposes this as the public Space URL.

---

### 5. Setting Up the Hugging Face Space (Step-by-step)

#### 5.1 Create a Docker Space

1. Go to: https://huggingface.co/spaces
2. Click **“Create new Space”**.
3. Choose:
   - **Space SDK**: `docker`
   - **Hardware**: `CPU basic` (free tier)
4. Pick a name, e.g., `your-username/jarvis-voice-agent-demo`.

#### 5.2 Add README metadata

In the **Space repo** (or in your fork if you push from there), ensure `README.md` in the Space root (not necessarily the project root) includes a header like:

```yaml
---
title: Jarvis Voice Agent – Demo Backend
sdk: docker
app_port: 7860
---
```

This tells HF:

- You are using the Docker SDK.
- The app listens on `PORT` (commonly `7860`).

#### 5.3 Connect your backend Dockerfile

You have two options:

**Option A – Copy backend folder into the Space repo**

1. Inside the Space repository, create a `backend/` directory.
2. Copy the repo’s `backend/` contents into the Space `backend/`.
3. In the Space root, create a `Dockerfile` like:

   ```dockerfile
   FROM python:3.11-slim

   ENV PYTHONUNBUFFERED=1 \
       PIP_NO_CACHE_DIR=1 \
       PORT=7860 \
       APP_ENV=prod

   WORKDIR /app
   COPY backend/requirements.txt .
   RUN python -m pip install --upgrade pip \
       &amp;&amp; pip install -r requirements.txt

   COPY backend/app ./app

   EXPOSE ${PORT}
   CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
   ```

**Option B – Use your repo as a subdirectory**

1. If your code lives elsewhere (e.g., GitHub), you can:
   - Use a CI process to build and push a tarball of `backend/` to the Space, or
   - Manually sync `backend/` into the Space repo as above.
2. The key is that the **Space Dockerfile** must be able to see:
   - `requirements.txt`
   - `app/` (the FastAPI package)

For this project, **Option A** (copying `backend/`) is typically simplest.

#### 5.4 Configure environment variables in the Space

In the Space **Settings → Variables and secrets**, set:

- `LLM_PROVIDER=llamacpp`
- `LOG_LEVEL=INFO`
- Optional (override defaults only if needed):
  - `LLAMACPP_MODEL_REPO=TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF`
  - `LLAMACPP_MODEL_FILE=tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`
  - `LLAMACPP_CONTEXT_LENGTH=2048`
  - `LLAMACPP_MAX_TOKENS=256`

Do **not** store any secrets here; this configuration only references **public** models and free infrastructure.

#### 5.5 Build and deploy

1. Push your changes to the Space repo.
2. HF will build the Docker image automatically.
3. During the first startup:
   - The container downloads the TinyLlama GGUF file from Hugging Face Hub.
   - Initializes the LlamaCpp model.
   - Logs a line indicating the model is **ready**.

You can monitor progress in the **Space logs**.

#### 5.6 Verify the deployment

Once the Space shows as **Running**:

1. Open `<your-space-url>/health`:
   - Expect: `{"status": "ok"}`.
2. Open `<your-space-url>/docs`:
   - You should see the FastAPI automatic documentation.
3. Try a `/chat` call from a tool like `curl` or Postman using the Space URL.

---

### 6. Cold Starts and Logs

Because the model is downloaded and initialized at startup:

- The **first cold start** may take several minutes.
- During that time:
  - `/health` may still be OK (backend is up).
  - `/chat` may return a **“demo degraded”** message if the model is not fully ready.
- You can view logs in:
  - The **“Logs”** tab of the HF Space.

Recommended workflow:

- Deploy once, wait for the model to initialize.
- Keep the Space **warm** while demoing; avoid letting it sleep if possible (HF may idle it on inactivity).

---

## Path 2 – Best “Jarvis Experience” (Local Backend + Cloudflare Tunnel)

For the best user experience (latency, privacy, free usage):

- Run **Ollama + backend on your own machine**.
- Expose the backend securely to the internet using **Cloudflare Tunnel** (`cloudflared`).
- Connect the mobile app (phone) to that tunnel URL.

This keeps all LLM work on your hardware while still allowing **any device** to connect.

---

### 1. Overview

- Local stack:
  - Ollama with `mistral`.
  - FastAPI backend on `http://localhost:8000`.
- Public access:
  - `cloudflared tunnel --url http://localhost:8000`
  - Cloudflare provides a random HTTPS URL like `https://&lt;random&gt;.trycloudflare.com`.
- Mobile:
  - Set **Backend base URL** in Settings to that HTTPS URL.

No paid services are required.

---

### 2. Install `cloudflared`

Follow Cloudflare’s official instructions:  
https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

Common examples:

- **macOS (Homebrew)**

  ```bash
  brew install cloudflared
  ```

- **Linux (Debian/Ubuntu)**

  ```bash
  sudo apt-get update
  sudo apt-get install cloudflared
  ```

- **Windows**

  - Download the installer from Cloudflare’s docs, or
  - Use `choco install cloudflared` if you have Chocolatey.

Verify:

```bash
cloudflared --version
```

---

### 3. Start backend locally on port 8000

Use the standard local run flow (or scripts):

#### macOS / Linux (bash)

```bash
./scripts/dev.sh
```

or:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Windows (PowerShell)

```powershell
.\scripts\dev.ps1
```

or:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ensure:

```bash
curl http://127.0.0.1:8000/health
```

returns `{ "status": "ok" }`.

---

### 4. Start Cloudflare Tunnel

In a **new terminal** (do not stop the backend), from anywhere:

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflare will:

- Establish an outbound tunnel from your machine to Cloudflare.
- Print a URL like:

```text
https://random-name-1234.trycloudflare.com
```

This URL is:

- Publicly reachable over HTTPS.
- Reverse‑proxies traffic to your local `http://localhost:8000`.

> This is ideal for short demos or testing with real devices. For long‑term production use, you would configure a named tunnel and custom domain, but that is out of scope for this free‑first runbook.

---

### 5. Configure the mobile app to use the tunnel

On your phone:

1. Install and run the Flutter app (see `context/RUN_LOCAL.md` for local run details).
2. Open **Settings → Backend base URL**.
3. Set the URL to the Cloudflare tunnel value, e.g.:

   ```text
   https://random-name-1234.trycloudflare.com
   ```

4. Save and return to the Assistant screen.
5. Start talking to Jarvis:
   - The phone sends `/chat` to the Cloudflare URL.
   - Cloudflare forwards to your local backend.
   - Backend calls **local Ollama** (fast, private, free).
   - Replies return via the tunnel.

---

### 6. Security and Rate Limiting Notes

- The current V1 API:
  - Has **no authentication**.
  - Is designed for **trusted, local** or small demo environments.
- With Cloudflare tunnel:
  - Anyone who guesses/obtains the URL could theoretically call `/chat`.
  - In practice, `*.trycloudflare.com` URLs are hard to guess, but:
    - Treat this as a **demo**, not as an internet-scale public API.
- Rate limiting:
  - If you add a rate limiter middleware in the future, ensure:
    - `/health` remains light and unprotected.
    - `/chat` is guarded against abuse.
- Secrets:
  - This repo intentionally commits **no secrets**.
  - Your local `.env` is not checked in.
  - The only sensitive content is whatever conversations you send, and they remain on your machine when using Cloudflare + local Ollama.

To **turn off** public access, just stop the `cloudflared` process (Ctrl+C).

---

## Mobile Distribution (Free)

### 1. Android – Build a release APK

You can distribute an **APK** file for free (no Play Store required).

#### 1.1 Build the APK

From the repo root:

```bash
cd mobile
flutter build apk --release
```

The output will be at:

```text
mobile/build/app/outputs/flutter-apk/app-release.apk
```

#### 1.2 Share the APK via GitHub Releases

1. Commit and push your code to GitHub.
2. In GitHub:
   - Go to **Releases** → **Draft a new release**.
   - Tag it (e.g., `v0.3.0`).
   - Give it a title and description.
   - **Upload** `app-release.apk` as a binary asset.
   - Publish the release.
3. Share the release URL with testers:
   - They can download the APK and install it manually.

> Testers will need to allow installation from **unknown sources** on their devices.

---

### 2. iOS – What’s free vs paid

- Building and running on the **iOS simulator** is free with Xcode + Flutter.
- Installing on physical devices and distributing via:
  - **App Store**, or
  - **TestFlight**
- …requires an **Apple Developer Program** membership, which is **paid**.

Recommended free‑first approach:

- Demo the app on the **iOS simulator** and **record the screen**.
- Share:
  - Source code,
  - Screen recordings,
  - Android APK (for hands‑on testing).
- If a user already has an Apple developer account and knows how to sideload apps:
  - They can build and install the app on their own device using Xcode or `flutter run -d &lt;device-id&gt;`.

---

## Deployment Checklist

Use this checklist before calling a deployment “done”.

### For Hugging Face Spaces (LlamaCpp demo)

- [ ] Backend code deployed with `backend/` and `Dockerfile` accessible.
- [ ] `requirements.txt` includes:
  - `llama-cpp-python`
  - `huggingface_hub`
- [ ] Environment variables set in Space:
  - [ ] `LLM_PROVIDER=llamacpp`
  - [ ] `LOG_LEVEL=INFO`
  - [ ] Optional overrides for `LLAMACPP_*` if needed.
- [ ] Space builds successfully (no pip/compile failures).
- [ ] First startup completes model download and initialization.
- [ ] `/health` and `/docs` return expected responses.
- [ ] Basic `/chat` call returns a coherent reply (or a “demo degraded” message on failure, but not a 500).

### For Local Backend + Cloudflare Tunnel

- [ ] Ollama installed, `mistral` pulled, and `ollama serve` running.
- [ ] Backend starts successfully on `0.0.0.0:8000`.
- [ ] `GET /health` is 200 from localhost.
- [ ] `cloudflared --version` works.
- [ ] `cloudflared tunnel --url http://localhost:8000` prints an HTTPS URL.
- [ ] Mobile app’s backend base URL is set to that HTTPS URL.
- [ ] End‑to‑end voice loop works from the phone over the tunnel.

### For Mobile Distribution (Android)

- [ ] `flutter build apk --release` succeeds.
- [ ] `app-release.apk` is present under `mobile/build/app/outputs/flutter-apk/`.
- [ ] APK uploaded as an asset to a GitHub Release.
- [ ] Release notes mention:
  - Supported platforms (Android).
  - Basic setup (backend URL configuration).

---

## Rollback / Troubleshooting

### Hugging Face Spaces

**Symptom:** Build fails (e.g., `llama-cpp-python` compilation error).

- Check Space build logs.
- Ensure the Space uses a supported Python version (3.11 is recommended).
- If needed, pin `llama-cpp-python` to a known-good version in `backend/requirements.txt`.

**Symptom:** Space runs but `/chat` always returns “demo degraded”.

- Likely the TinyLlama model failed to download or initialize.
- Check logs for:
  - Network issues reaching Hugging Face Hub.
  - Disk space or memory constraints.
- Actions:
  - Confirm the model repo/file names match those in the Space environment variables.
  - Redeploy with a smaller context window (`LLAMACPP_CONTEXT_LENGTH`) or lower `LLAMACPP_MAX_TOKENS`.

**Rollback:**

- Revert the Space to a previous commit that you know worked.
- Or temporarily set `LLM_PROVIDER=ollama` and point `OLLAMA_BASE_URL` to a remote Ollama instance you control (advanced; not needed for typical free demos).

---

### Local Backend + Cloudflare Tunnel

**Symptom:** Tunnel URL works, but `/health` fails.

- Check that the backend is started **before** running `cloudflared`.
- Ensure `cloudflared` command points to the correct local URL:

  ```bash
  cloudflared tunnel --url http://localhost:8000
  ```

**Symptom:** Backend works on localhost but not via tunnel.

- Some security software or firewalls may interfere.
- Try another machine / network if possible.
- Check Cloudflare logs and tunnel output for error messages.

**Rollback:**

- Stop the tunnel (`Ctrl+C`).
- Your backend remains local‑only; no external access.

---

### Mobile App

**Symptom:** “Unable to reach backend” or similar error snackbars.

- Confirm:
  - Backend URL in Settings is correct.
  - For local dev:
    - Emulator → `http://10.0.2.2:8000`
    - iOS simulator → `http://127.0.0.1:8000`
  - For Cloudflare tunnel:
    - Backend URL is the HTTPS tunnel URL from `cloudflared`.
- If necessary, rebuild and reinstall the app:

  ```bash
  cd mobile
  flutter clean
  flutter pub get
  flutter run
  ```

---

These two deployment paths keep the system **free**, **local-first**, and **portable**:

- HF Spaces + LlamaCpp: easy public demo of `/chat` without running Ollama in the cloud.
- Local + Cloudflare tunnel: best Jarvis experience using your own hardware, accessible from any device.