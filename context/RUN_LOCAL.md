# Running Jarvis Voice Agent Locally

This runbook makes it **turnkey** to run the full Jarvis stack (Ollama + FastAPI backend + Flutter mobile) on your own machine.

All commands assume you are at the **repository root** (the folder containing `backend/` and `mobile/`) unless otherwise noted.

---

## 1. What You Need Installed

Install these tools **before** you start.

### 1.1 Cross‑platform prerequisites (all OS)

1. **Git**
   - Download: https://git-scm.com/downloads
   - Verify:

     ```bash
     git --version
     ```

2. **Python** (3.10+ or 3.11 recommended) with `pip` and `venv`
   - Download: https://www.python.org/downloads/
   - Verify (any one of these is fine, depending on your system):

     ```bash
     python --version
     python3 --version
     ```

3. **Flutter SDK + Dart**
   - Install: https://docs.flutter.dev/get-started/install
   - Verify:

     ```bash
     flutter --version
     ```

4. **Android Studio + Android SDK / Emulator**
   - Install Android Studio: https://developer.android.com/studio
   - Inside Android Studio:
     - Install **Android SDK** + platform tools.
     - Create at least one **Android Virtual Device (AVD)** (Android emulator).
   - Verify emulator list:

     ```bash
     flutter emulators
     ```

5. **Xcode** (macOS only, for iOS simulator/device)
   - Install via App Store.
   - After install:

     ```bash
     xcode-select --install
     ```

   - Open Xcode once to accept licenses and install components.
   - iOS simulator is bundled with Xcode.

6. **Ollama** (Windows/macOS/Linux)
   - Install from https://ollama.ai
   - Verify:

     ```bash
     ollama --version
     ```

7. **Optional: GNU Make**
   - macOS:
     - Comes with Xcode Command Line Tools (`xcode-select --install`).
   - Linux:
     - Install via package manager (e.g. `sudo apt-get install make`).
   - Windows:
     - Use **Git Bash**, **WSL**, or other environments that ship `make`.
   - Verify:

     ```bash
     make --version
     ```

---

## 2. Repository Setup

### 2.1 Clone the repository

**All OS (bash or PowerShell):**

```bash
git clone &lt;YOUR_FORK_OR_CLONE_URL&gt; jarvis-voice-agent
cd jarvis-voice-agent
```

> Everything below assumes you are inside this `jarvis-voice-agent` folder.

---

### 2.2 Create backend virtual environment

You can do this using **bash**, **PowerShell**, or **Make**.

#### macOS / Linux (bash)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

If your Python command is `python` instead of `python3`, use:

```bash
python -m venv .venv
source .venv/bin/activate
```

#### Windows (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If `ExecutionPolicy` blocks script execution, run PowerShell **as Administrator** and:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then re-run the activation command.

#### Using Make (macOS / Linux / Git Bash / WSL)

From the **repo root**:

```bash
make backend-venv
```

This creates `backend/.venv`. To activate it manually:

```bash
cd backend
source .venv/bin/activate
```

---

### 2.3 Install backend dependencies

#### macOS / Linux (bash)

From `backend/` with the virtualenv activated:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Windows (PowerShell)

From `backend\` with the virtualenv activated:

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

#### Using Make

From the repo root:

```bash
make backend-install
```

This will:

- Create `backend/.venv` if needed.
- Install `backend/requirements.txt` into that virtualenv.

---

### 2.4 Configure backend environment (`.env`)

The backend reads configuration from environment variables. For local use we keep a simple, checked‑in example file.

#### Create `.env` from example

From **`backend/`**:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `backend/.env` in your editor and adjust if needed. Defaults are safe:

- `LLM_PROVIDER=ollama` (local Ollama is the default)
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=mistral`
- `CORS_ALLOW_ORIGINS` includes common local URLs (backend, emulator, etc.)

> Do **not** commit `.env` to git. It is for local configuration only.

---

### 2.5 Install Flutter dependencies

From the repo root:

#### macOS / Linux (bash)

```bash
cd mobile
flutter pub get
```

#### Windows (PowerShell)

```powershell
cd mobile
flutter pub get
```

#### Using Make

From the repo root:

```bash
make mobile-get
```

---

## 3. Run Ollama + Pull the Model

The backend expects a **local Ollama** instance by default.

### 3.1 Start Ollama service

On some platforms, installing Ollama also installs and starts a background service. If unsure, start it manually:

#### macOS / Linux (bash)

```bash
ollama serve
```

Keep this terminal open while you use the app.

#### Windows (PowerShell)

```powershell
ollama serve
```

You can also start Ollama via the desktop app and leave it running.

### 3.2 Pull the default model (`mistral`)

The backend default is `mistral` (see `backend/app/core/config.py` and `.env.example`).

#### All OS

```bash
ollama pull mistral
```

You only need to pull the model once; it is cached locally.

### 3.3 Verify Ollama is reachable

#### macOS / Linux (bash)

Check the **tags** endpoint:

```bash
curl http://localhost:11434/api/tags
```

You should see JSON including `"mistral"` in the `models` list.

Send a **simple chat** request:

```bash
curl http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      { "role": "user", "content": "Say hello in one short sentence." }
    ],
    "stream": false
  }'
```

#### Windows (PowerShell)

```powershell
Invoke-WebRequest `
  -Uri "http://localhost:11434/api/tags" `
  -UseBasicParsing
```

Chat test:

```powershell
Invoke-WebRequest `
  -Uri "http://localhost:11434/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{
    "model": "mistral",
    "messages": [
      { "role": "user", "content": "Say hello in one short sentence." }
    ],
    "stream": false
  }' `
  -UseBasicParsing
```

If these succeed, the backend will be able to talk to Ollama.

---

## 4. Run the Backend (FastAPI)

The backend runs with **uvicorn** and listens on **`0.0.0.0:8000`**.

### 4.1 macOS / Linux (bash)

From the repo root:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

This starts the API with auto‑reload for local development.

### 4.2 Windows (PowerShell)

From the repo root:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.3 Using Make (macOS / Linux / Git Bash / WSL)

From the repo root:

```bash
make backend-dev
```

This will:

- Use `backend/.venv` if present.
- Start `uvicorn app.main:app` on `0.0.0.0:8000` with reload.

### 4.4 Using convenience scripts

From the repo root:

#### macOS / Linux (bash)

```bash
./scripts/dev.sh
```

This script:

- Checks if Ollama is reachable at `http://localhost:11434`.
- Starts the backend on `http://0.0.0.0:8000`.
- Prints useful URLs.

Make it executable if needed:

```bash
chmod +x scripts/dev.sh
```

#### Windows (PowerShell)

```powershell
.\scripts\dev.ps1
```

This script:

- Checks Ollama at `http://localhost:11434/api/tags`.
- Activates `backend\.venv` if present.
- Runs `uvicorn` on `0.0.0.0:8000`.

---

### 4.5 Health check

Once the backend is running:

#### macOS / Linux (bash)

```bash
curl http://127.0.0.1:8000/health
```

#### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
```

Expected JSON:

```json
{ "status": "ok" }
```

### 4.6 Example `/chat` request

Minimal example payload that matches `context/API_CONTRACT.md`:

```bash
curl http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "local-session",
    "messages": [
      {
        "role": "user",
        "content": "What can you help me with?",
        "ts": "2024-01-26T12:34:56Z"
      }
    ],
    "client": {
      "platform": "android",
      "app_version": "0.1.0"
    },
    "settings": {
      "response_style": "normal"
    }
  }'
```

On success you will see a JSON `ChatResponse` with `reply_text` and `debug.latency_ms`.

---

## 5. Run the Mobile App

The mobile app is in `mobile/` and uses Flutter.

### 5.1 Ensure backend + Ollama are running

Before starting the mobile app:

- Ollama running and serving `mistral`.
- Backend running on `http://0.0.0.0:8000`.

You can verify with the health check in section 4.5.

### 5.2 Android emulator

#### Start an emulator

You can start an AVD via Android Studio, or:

```bash
flutter emulators
flutter emulators --launch &lt;emulator_id&gt;
```

#### Run the app (Android)

From the repo root:

- **macOS / Linux (bash)**

  ```bash
  cd mobile
  flutter pub get
  flutter run -d emulator-5554   # or your emulator ID
  ```

- **Windows (PowerShell)**

  ```powershell
  cd mobile
  flutter pub get
  flutter run -d emulator-5554   # or your emulator ID
  ```

- **Using Make (any OS with make + Flutter)**

  ```bash
  make mobile-run-android
  ```

  This runs `flutter run` in `mobile/` and lets Flutter pick the default Android device.

### 5.3 iOS simulator (macOS only)

From the repo root:

```bash
cd mobile
flutter pub get
open -a Simulator        # Opens the iOS Simulator
flutter run -d ios       # Or pick a specific simulator from `flutter devices`
```

### 5.4 API base URL per platform

The default base URLs are defined in `mobile/lib/core/config.dart`:

- **Android emulator:** `http://10.0.2.2:8000`
- **iOS simulator:** `http://localhost:8000`
- **Physical device:** `http://&lt;LAN_IP&gt;:8000`

You can also override the backend base URL at runtime:

1. Open the app.
2. Go to **Settings → Backend base URL**.
3. Enter the correct URL, for example:

   - Android emulator: `http://10.0.2.2:8000`
   - iOS simulator: `http://127.0.0.1:8000`
   - Physical device: `http://192.168.1.10:8000` (replace with your machine’s IP)

### 5.5 Physical Android device

1. Ensure your phone and backend machine are on the **same Wi‑Fi network**.
2. Find your machine’s local IP:

   - macOS / Linux:

     ```bash
     ip addr    # or: ifconfig
     ```

   - Windows (PowerShell):

     ```powershell
     ipconfig
     ```

3. In the app Settings, set **Backend base URL** to:

   ```text
   http://&lt;YOUR_MACHINE_LAN_IP&gt;:8000
   ```

4. Run the app on the device:

   ```bash
   cd mobile
   flutter run -d &lt;device_id&gt;
   ```

### 5.6 Microphone permissions

- On first use, the app will request **microphone permission**.
- If you **deny** it:
  - The assistant will not be able to capture speech.
  - You may see error snackbars like “Microphone permission is required”.

To re‑enable:

- **Android:**
  - Settings → Apps → Jarvis Voice Agent → Permissions → Microphone → Allow.
- **iOS:**
  - Settings → Jarvis Voice Agent → Microphone → Enable.

---

## 6. Running Tests, Formatting, and Linting

### 6.1 Backend tests

#### macOS / Linux (bash)

```bash
cd backend
source .venv/bin/activate
pytest
```

#### Windows (PowerShell)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

#### Using Make

From the repo root:

```bash
make backend-test
```

---

### 6.2 Format & lint

Using the root `Makefile`:

```bash
# Format backend Python code with ruff
make format

# Lint backend + run Flutter analyze
make lint
```

---

## 7. Troubleshooting

### 7.1 Backend cannot reach Ollama

Symptoms:

- `/chat` replies with friendly error mentioning it cannot reach the local language model.
- Backend logs contain `ollama_connection_error` or similar.

Checks:

1. Is Ollama running?

   ```bash
   curl http://localhost:11434/api/tags
   ```

   If this fails, start it:

   ```bash
   ollama serve
   ```

2. Is `OLLAMA_BASE_URL` correct?

   - Check `backend/.env`:

     ```env
     OLLAMA_BASE_URL=http://localhost:11434
     ```

   - If your backend runs in Docker, you may need:
     - `http://host.docker.internal:11434` (macOS/Windows)
     - A specific host IP (Linux).

3. Is the model pulled?

   ```bash
   ollama pull mistral
   ```

---

### 7.2 CORS errors (mainly for web/browser clients)

Symptoms (in browser devtools):

- `Access to fetch at 'http://localhost:8000/chat' from origin 'http://localhost:3000' has been blocked by CORS policy...`.

Checks:

1. Confirm `CORS_ALLOW_ORIGINS` in `backend/.env` includes your origin(s), e.g.:

   ```env
   CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:8000,http://10.0.2.2:8000
   ```

2. Restart the backend after changing `.env`.

> The **mobile app** uses HTTP directly and typically does not hit browser CORS, but these settings matter if you build a web client.

---

### 7.3 Emulator cannot reach localhost

Symptoms:

- Android emulator shows network errors or “Unable to reach backend”.
- Backend health check works on the host machine.

Fix:

- For Android emulator, **never** use `http://localhost:8000` inside the app.
- Use:

  ```text
  http://10.0.2.2:8000
  ```

- For iOS simulator, `http://127.0.0.1:8000` or `http://localhost:8000` is correct.
- For physical devices, use `http://&lt;LAN_IP&gt;:8000`.

Update the **Backend base URL** in the app Settings accordingly.

---

### 7.4 “No speech recognized” / STT issues

Symptoms:

- You tap the mic, speak, release, but the transcript stays empty.
- Snackbars mention no speech detected or microphone issues.

Checks:

1. Confirm microphone permission is **allowed** (see section 5.6).
2. Speak clearly and closer to the microphone; background noise can confuse STT.
3. On some devices, short utterances may time out quickly. Try speaking for 2–3 seconds.
4. If issues persist, fully quit and restart the app; on some platforms the OS STT service can get stuck.

Backend is **not** involved in STT; this is entirely device/OS-level.

---

### 7.5 Ports already in use

Symptoms:

- Starting uvicorn prints errors like `OSError: [Errno 98] Address already in use`.

Checks:

1. See which process is using port **8000**.

   - macOS / Linux:

     ```bash
     lsof -i :8000
     ```

   - Windows (PowerShell):

     ```powershell
     netstat -ano | Select-String ":8000"
     ```

2. Either stop the conflicting process **or** change the backend port:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

3. Update the mobile app **Backend base URL** to match the new port, e.g.:

   ```text
   http://10.0.2.2:8001        # Android emulator
   http://127.0.0.1:8001       # iOS simulator
   http://&lt;LAN_IP&gt;:8001        # Physical device
   ```

---

### 7.6 General tips

- If you change `.env`, **restart** the backend.
- If you change `Config.baseUrl` behavior or other mobile code, run:

  ```bash
  cd mobile
  flutter clean
  flutter pub get
  flutter run
  ```

- Backend logs include a `request_id` you can use to correlate requests and problems.