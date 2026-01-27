# Architecture Overview

This document describes the high-level architecture for the **Jarvis Voice Agent** and how the main voice loop works end-to-end.

---

## High-Level Components

- **Mobile app (Flutter)**
  - Push-to-talk UI (`AssistantScreen`) with:
    - Mic button
    - Status indicator
    - Live transcript
    - Response text
    - Simple chat history
  - Settings UI (`SettingsScreen`) for response style, TTS rate, and backend base URL.
  - On-device Speech-to-Text (STT) using the `speech_to_text` package.
  - On-device Text-to-Speech (TTS) using the `flutter_tts` package.
  - HTTP client to call the backend `/chat` endpoint.

- **Backend (FastAPI)**
  - `/health` endpoint for liveness checks.
  - `/chat` endpoint for conversational requests.
  - Pydantic schemas for input/output validation.
  - Centralized configuration & logging.
  - Integration with **Ollama** via its REST API.

- **Local LLM (Ollama)**
  - Runs on the same machine as the backend.
  - Default base URL: `http://localhost:11434`
  - Chat API endpoint: `POST /api/chat`

- **Context folder (`context/`)**
  - Human- and machine-readable project documentation.
  - Used to build system prompts (prompt builder reads small excerpts from `GOAL.md` and `COMPONENTS.md`).

---

## Sequence Diagram – Voice Loop

Text-based sequence diagram for the main interaction:

```text
User
 │
 │ 1. Tap mic button
 ▼
Flutter App (AssistantScreen)
 │
 │ 2. Request microphone permission
 │ 3. Start on-device STT (speech_to_text)
 │
 ▼
On-device STT
 │
 │ 4. Stream partial transcripts → UI
 │ 5. Produce final recognized text
 │
 ▼
Flutter App
 │
 │ 6. Build ChatRequest payload:
 │      - session_id
 │      - messages (history + latest user message)
 │      - client (platform + app_version)
 │      - settings (response_style)
 │
 │ 7. HTTP POST /chat
 ▼
FastAPI Backend (/chat)
 │
 │ 8. Validate ChatRequest with Pydantic schemas
 │ 9. Build system prompt:
 │      - Load excerpts from context/GOAL.md and context/COMPONENTS.md
 │      - Compose concise instructions for the LLM
 │
 │ 10. Compose Ollama messages:
 │       - system message (from prompt builder)
 │       - conversation history (user/assistant messages)
 │
 │ 11. Call Ollama REST API:
 │       POST {OLLAMA_BASE_URL}/api/chat
 │       Payload:
 │         {
 │           "model": OLLAMA_MODEL,
 │           "messages": [...],
 │           "stream": false
 │         }
 │
 │ 12. Handle response or failure:
 │       - On success: extract reply_text
 │       - On network error: retry; if still failing, produce fallback reply
 │       - Never expose stack trace to client, but log with request_id
 │
 │ 13. Measure latency_ms
 │ 14. Return ChatResponse:
 │       {
 │         "session_id": ...,
 │         "reply_text": ...,
 │         "debug": {"model": ..., "latency_ms": ...},
 │         "errors": [...]
 │       }
 ▼
Flutter App
 │
 │ 15. Parse ChatResponse
 │ 16. Update chat history with assistant reply
 │ 17. Display reply_text in UI
 │ 18. Invoke on-device TTS (flutter_tts) to speak reply
 │
 ▼
User hears spoken response
```

---

## STT/TTS Technology Choices

- **STT – `speech_to_text`**
  - Uses the device’s built-in speech recognition services.
  - This is **free-first** and typically runs on-device or via OS-level services.
  - We do **not** depend on any paid cloud STT provider.

- **TTS – `flutter_tts`**
  - Uses the device’s native TTS engines.
  - Also **free-first** and runs via OS-level capabilities.

The system is designed so that swapping STT/TTS engines later (e.g., adding a local model or a different plugin) should be localized to the assistant feature layer.

---

## Backend ↔ Ollama Integration

- **Base URL**
  - Configured via `OLLAMA_BASE_URL` environment variable.
  - **Default:** `http://localhost:11434`
  - The backend will call: `POST {OLLAMA_BASE_URL}/api/chat`

- **Payload shape**

The backend sends:

```json
{
  "model": "mistral",
  "messages": [
    {"role": "system", "content": "..." },
    {"role": "user", "content": "..." },
    {"role": "assistant", "content": "..." }
  ],
  "stream": false
}
```

- **Timeouts & retries**
  - Request timeout controlled by `REQUEST_TIMEOUT_S` (default `60` seconds).
  - The Ollama client performs a small number of retries on network errors.
  - If the client cannot reach Ollama, it raises a typed exception that the `/chat` router converts into a **friendly fallback reply**.

---

## Data & State

- **Conversation state (V1)**
  - Stored in-memory in the Flutter app for the current session.
  - The data model supports:
    - `session_id`
    - message `role`, `content`, and timestamp.
  - This is intentionally structured so local persistence (e.g., SQLite/Hive) can be added later without changing the backend API.

- **Backend state**
  - Stateless per request; no database in V1.
  - All conversation context is carried in the `messages` array in the request.

---

## Environments & Configuration

- **Backend configuration** (from environment variables):
  - `APP_ENV` – `local` (default), `dev`, or `prod`.
  - `LOG_LEVEL` – `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, `CRITICAL`.
  - `OLLAMA_BASE_URL` – base URL of Ollama (default `http://localhost:11434`).
  - `OLLAMA_MODEL` – default model name (e.g., `mistral`).
  - `REQUEST_TIMEOUT_S` – HTTP timeout in seconds (default `60`).
  - `CORS_ALLOW_ORIGINS` – comma-separated list of origins allowed for local dev.

- **Mobile configuration**
  - Default backend base URL:
    - Android emulator: `http://10.0.2.2:8000`
    - iOS simulator / desktop: `http://localhost:8000`
  - The value can be changed at runtime from the `SettingsScreen`.

---

## Logging & Observability

- **Backend**
  - Centralized logging configuration with a consistent format:
    - timestamp, level, logger name, `request_id`, message.
  - `RequestIdMiddleware` generates or propagates `X-Request-ID`.
  - `/chat` logs:
    - start/end of requests
    - errors from Ollama (categorized as connection vs response errors)
    - latency measurements

- **Mobile**
  - Lightweight logger wrapper for tagged logs.
  - Controllers catch exceptions, log details, and surface friendly error messages to the user (no raw stack traces in UI).

---

## Extensibility Notes

The architecture is intentionally simple but:

- Clear separation between:
  - UI (screens)
  - Controllers (state, orchestration)
  - Services (HTTP, device APIs)
  - Backend schemas, services, and routers.
- This should make it straightforward to add:
  - New skills (e.g., weather, reminders).
  - Local persistence of history.
  - Cloud sync layers or remote backends.
- Context-aware prompts are built by `prompt_builder` using `context/` files, so improving prompts is mostly a matter of updating those files and the builder logic.