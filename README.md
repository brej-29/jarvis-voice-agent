# Jarvis Voice Agent

Push-to-talk, Jarvis-style voice assistant built with:

- **Flutter** mobile app (Android/iOS) for STT → UI → TTS.
- **FastAPI** backend that calls a local **Ollama** LLM.
- **Free-first**: on-device STT/TTS via Flutter packages and a local Ollama instance. No paid cloud dependencies.

This is **V1** of the project, focused on a single, local voice loop.

For detailed runbooks, see:

- `context/RUN_LOCAL.md` – step-by-step local setup (backend + mobile).
- `context/DEPLOY_FREE.md` – free deployment options (HF Spaces + Cloudflare tunnel + Android APK).

---

## Prerequisites

- **Ollama** installed and running locally  
  See: https://ollama.ai

- **Python** (3.11 recommended) for the backend
- **Flutter** (stable channel) for the mobile app

---

## 1. Run Ollama and Pull the Model

1. Install and start Ollama.
2. Pull the model specified in backend config (default: `mistral`):

   ```bash
   ollama pull mistral
   ```

3. Ensure Ollama is running and listening on the default port:

   ```bash
   ollama serve
   ```

   The backend expects Ollama at `http://localhost:11434` by default (configurable via `OLLAMA_BASE_URL`).

---

## 2. Run the Backend (FastAPI)

From the repo root:

```bash
cd backend

# Optional: create a virtualenv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Copy the example environment file and adjust if needed:

```bash
cp .env.example .env
```

Run the FastAPI app with uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

- `GET http://localhost:8000/health` → `{"status": "ok"}`

Chat endpoint (used by the mobile app):

- `POST http://localhost:8000/chat`

The contract for `/chat` is defined in:

- `context/API_CONTRACT.md`

---

## 3. Run the Flutter App (Mobile)

From the repo root:

```bash
cd mobile
flutter pub get
flutter run
```

### Backend Base URL

By default:

- **Android emulator** uses `http://10.0.2.2:8000`
- **iOS simulator / desktop** typically uses `http://localhost:8000`

The current base URL is:

- Defined in `lib/core/config.dart`.
- Editable at runtime from **Settings → Backend base URL**.

---

## 4. Voice Loop (End-to-End)

On the **Assistant screen**:

1. Tap the **mic button**:
   - App requests microphone permission.
   - Starts on-device STT (via `speech_to_text`).
   - Shows partial transcript as you speak.

2. Release / tap again:
   - STT stops and final text is captured.
   - App sends a `ChatRequest` to `/chat` on the backend.
   - Backend calls Ollama `/api/chat`, builds a reply, and returns `reply_text`.

3. The app:
   - Displays the reply text.
   - Speaks it via on-device TTS (`flutter_tts`).
   - Adds both user and assistant messages to the local session history list.

Error states (permission denied, no speech detected, backend unreachable) are surfaced as snackbars with friendly messages. Detailed errors are logged on-device and in the backend logs, not shown directly to end users.

---

## 5. Settings

The **Settings screen** lets you:

- Choose **response style**: `concise`, `normal`, `detailed`.
- Adjust **TTS rate** (speech speed).
- Configure the **backend base URL** for different environments/devices.

The chosen settings are applied to new chat requests and TTS playback.

---

## 6. CI / Tests

Basic CI is provided via GitHub Actions:

- Backend:
  - Install dependencies from `backend/requirements.txt`.
  - Run `ruff` linting and format checks.
  - Run `pytest` tests (`backend/tests`).
- Mobile:
  - Run `flutter pub get`.
  - Run `flutter analyze`.
  - Run `flutter test`.

To run backend tests locally:

```bash
cd backend
pytest
```

---

## Known Limitations (V1)

- **No wake word** yet – interaction is **push-to-talk** only.
- **No persistent storage** of conversation history – state is in-memory on the device.
- **Local-only LLM** – assumes Ollama is running on the same machine as the backend.
- **Single client focus** – optimized for one local mobile client talking to a local backend.

Future work (V2+) is outlined in:

- `context/GOAL.md`
- `context/ARCHITECTURE.md`
- `context/DECISIONS.md`
- `context/CHANGELOG.md`