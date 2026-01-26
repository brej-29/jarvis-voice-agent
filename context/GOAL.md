# Jarvis Voice Agent – Product Goal and Scope

## Product Goal

Build a **push-to-talk, Jarvis-style voice assistant** that:
- Feels responsive and low-latency for short, conversational queries.
- Runs **free-first**: on-device STT/TTS and a **local Ollama LLM backend**.
- Works reliably in **offline / constrained environments** (no hard dependency on cloud APIs).
- Is easy to extend with new skills (e.g., weather, reminders) and cross-device sync later.

The assistant should feel like a persistent companion that understands short-term context within a session and can be expanded into a broader “personal console” for the user.

---

## V1 Scope (This Repo)

**Primary user journey**

1. User holds/taps a mic button in the Flutter app.
2. On-device STT converts speech → text.
3. Text is sent to the FastAPI backend `/chat` endpoint.
4. Backend calls a local Ollama model to generate a reply.
5. Reply text is returned to the app and spoken via on-device TTS.
6. The conversation history is stored **locally on the device** (in-memory for v1, but code structured so that persistence/sync can be added).

**Technical scope**

- **Mobile (Flutter)**
  - Single app with:
    - `AssistantScreen`: mic button, status indicator, transcript, response text, and local chat history.
    - `SettingsScreen`: response style, TTS rate, backend base URL for local dev/device.
  - STT: `speech_to_text` (uses platform’s on-device speech services where possible).
  - TTS: `flutter_tts` (on-device voices).
  - HTTP client to call backend `/chat`.
  - Basic error handling and logging surfaced as toasts/snackbars/banners.

- **Backend (FastAPI)**
  - `/health` endpoint for liveness checks.
  - `/chat` endpoint:
    - Accepts structured `ChatRequest` payload.
    - Calls Ollama REST API `/api/chat`.
    - Injects a minimal system prompt derived from `context/` files.
    - Returns `ChatResponse` with `reply_text`, debug info, and structured error list.
  - Config via environment variables, with safe defaults.
  - Centralized logging, request IDs, and robust exception handling (no stack traces in responses).

- **Context**
  - `context/` folder as **source of truth** for product and technical intent.
  - Used to build system prompts and to guide future contributors/AI agents.

- **Testing & CI**
  - Minimal backend tests (health check and schema validation).
  - Basic CI:
    - Backend: install deps, ruff lint/format check, pytest.
    - Flutter: `flutter analyze` and basic `flutter test`.

---

## V2 Scope (Future, Not in This PR)

These are **explicitly out of scope** for V1 but should inform how we structure the code:

- **Persistence & Sync**
  - Durable local storage of conversation history (e.g., SQLite, Hive, Isar).
  - Optional cloud sync for multi-device continuity (while respecting “free-first” and privacy constraints).
  - Session management, multi-session history, and search.

- **Skills & Integrations**
  - Weather via **Open-Meteo** (free API).
  - Local reminders and alarms (stored and managed on-device).
  - Simple tool-calling / function-calling pattern from the LLM to trigger skills.

- **Experience Enhancements**
  - Wake-word support (hotword detection) instead of push-to-talk.
  - Richer UI: avatars, streaming transcript, partial TTS, etc.
  - Background mode, headphones integration, better audio UX.

- **Architecture**
  - Pluggable model backends (switchable Ollama models, other local models).
  - Modular skill system with explicit contracts and safety checks.

---

## Free-First Constraints

- **No paid cloud dependencies** in core flow:
  - STT/TTS must rely on **on-device / OS-provided capabilities** via Flutter packages.
  - LLM must run via **local Ollama** (`http://localhost:11434` by default).
- Any future optional cloud features must be:
  - Clearly marked as optional.
  - Gracefully degradable when offline or misconfigured.
- Telemetry, logging, and analytics must avoid sending user content off-device in default configuration.

---

## Definitions of Done (V1)

V1 is considered **done** when:

1. **Repo structure**
   - Matches the structure described in `context/ARCHITECTURE.md` and the main task description.
   - `context/` files are populated and are the primary documentation.

2. **Backend**
   - FastAPI app starts without errors.
   - `GET /health` returns HTTP 200 with a simple JSON payload.
   - `POST /chat`:
     - Accepts the specified JSON payload.
     - Calls Ollama `/api/chat` with appropriate messages.
     - Returns `reply_text` and `debug.latency_ms`.
     - Provides a friendly fallback reply if Ollama is unavailable (no unhandled exceptions or stack traces in responses).
   - Logging:
     - Request-scoped request IDs.
     - Helpful, structured logs for normal requests and failures.

3. **Mobile app**
   - Runs on emulator/device.
   - `AssistantScreen`:
     - Mic button starts STT, shows partial/final transcript.
     - Sends final transcript to backend.
     - Displays backend reply and speaks it via TTS.
     - Shows local chat history for the current session.
   - `SettingsScreen`:
     - Allows selecting response style.
     - Allows adjusting TTS rate.
     - Allows configuring backend base URL.
   - Errors:
     - Mic permission errors, no speech, and backend failures surface as visible, user-friendly messages.

4. **Tests & CI**
   - Backend tests pass locally and in CI.
   - CI runs for the `feat/jarvis-v1` branch and validates:
     - Backend lint + tests.
     - Flutter analyze + tests.

5. **Change discipline**
   - Any behavior changes update:
     - `context/DECISIONS.md`
     - `context/CHANGELOG.md`
   - Future contributors (including AI agents) can understand “why” from these files without guessing.