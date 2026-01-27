# Components Overview

This document describes the main components of the Jarvis Voice Agent codebase and how they fit together.

---

## Repository Layout

At a high level:

```text
/
  README.md
  .gitignore
  context/
    GOAL.md
    ARCHITECTURE.md
    COMPONENTS.md
    API_CONTRACT.md
    COSINE_GROUNDING.md
    DECISIONS.md
    CHANGELOG.md
  backend/
    app/
      core/
      schemas/
      services/
      routers/
    tests/
    requirements.txt (or pyproject.toml, depending on choice)
    .env.example
  mobile/
    pubspec.yaml
    lib/
      core/
      features/
        assistant/
        settings/
    android/...
    ios/...
```

This structure is designed to:

- Keep **context** close to the code, for humans and AI tools.
- Separate **backend** (API + LLM integration) from **mobile** (Flutter UI).
- Allow future multi-platform clients to reuse the same backend contract.

---

## Context Layer (`context/`)

**Purpose:** Source of truth for product goals, architecture, decisions, and API contracts.

Files:

- `GOAL.md`
  - Product intent, V1 and V2 scope, free-first constraints, and definition of done.

- `ARCHITECTURE.md`
  - High-level system design and sequence diagrams.
  - Describes the voice loop: mic → STT → backend → LLM → TTS.

- `COMPONENTS.md`
  - You are here.
  - Maps out major components and their responsibilities.

- `API_CONTRACT.md`
  - Canonical specification of the `/chat` request and response formats.

- `COSINE_GROUNDING.md`
  - Guidance for future Cosine tasks and AI agents on how to use context files.
  - Defines the “change discipline” for keeping context in sync with behavior.

- `DECISIONS.md`
  - Architecture and product decisions with rationale.
  - Acts as a living ADR (Architecture Decision Record) log.

- `CHANGELOG.md`
  - Human-readable changelog of notable changes to the system.

The backend’s `prompt_builder` reads small, curated excerpts from `GOAL.md` and `COMPONENTS.md` to construct a concise system prompt, keeping LLM context grounded without excessive token usage.

---

## Backend (`backend/`)

### Core

- `backend/app/core/config.py`
  - Reads and validates environment variables:
    - `APP_ENV`, `LOG_LEVEL`
    - `LLM_PROVIDER` (`ollama` or `llamacpp`)
    - `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
    - `LLAMACPP_MODEL_REPO`, `LLAMACPP_MODEL_FILE`, `LLAMACPP_CONTEXT_LENGTH`, `LLAMACPP_MAX_TOKENS`
    - `REQUEST_TIMEOUT_S`, and `CORS_ALLOW_ORIGINS`.
  - Provides a `settings` object used across the backend.
  - Ensures sane defaults and logs warnings for invalid configuration.

- `backend/app/core/logging.py`
  - Centralized logging configuration:
    - Request ID filter (propagated via `X-Request-ID` header).
    - Structured log format: timestamp, level, logger, request_id, message.
  - `RequestIdMiddleware`:
    - Assigns a request ID per request.
    - Ensures the same ID is used in all logs and echoed back to the client.

### Schemas

- `backend/app/schemas/chat.py`
  - Pydantic models:
    - `ChatMessage`, `ChatRequest`, `ChatResponse`, client info, and settings.
  - Enforces:
    - Valid message roles (`user`, `assistant`, `system`).
    - Maximum content length.
    - Reasonable bounds on message count.
  - Serves as the single source of truth for the backend API’s JSON schema.

### Services

- `backend/app/services/ollama_client.py`
  - Thin wrapper around the Ollama `/api/chat` endpoint.
  - Handles:
    - HTTP POST to `{OLLAMA_BASE_URL}/api/chat` with `{"model": ..., "messages": [...], "stream": false}`.
    - Timeouts and network errors with small retry logic.
    - Typed exceptions (`OllamaClientError`, etc.) for the router to handle.
  - Never returns raw HTTP errors directly to the client.

- `backend/app/services/llamacpp_client.py`
  - CPU-only LlamaCpp provider for TinyLlama GGUF models.
  - Used when `LLM_PROVIDER=llamacpp` (e.g., Hugging Face Spaces demos).
  - Handles:
    - Downloading GGUF weights via `huggingface_hub.hf_hub_download`.
    - Initializing `llama-cpp-python` with a moderate context window.
    - Threaded inference with robust error handling (`LlamaCppClientError`, etc.).
  - Returns a plain string reply, mirroring the Ollama client interface.

- `backend/app/services/prompt_builder.py`
  - Reads excerpts from `context/GOAL.md` and `context/COMPONENTS.md`.
  - Builds a concise system prompt for the LLM.
  - Designed to be easily extendable if new context files are added later.

- `backend/app/services/weather.py`
  - Integrates with **Open-Meteo**'s free APIs:
    - Geocoding (`https://geocoding-api.open-meteo.com`) to resolve city names (optional).
    - Forecast (`https://api.open-meteo.com`) to retrieve current weather.
  - Provides:
    - `get_weather_description(...)` for a short, natural-language summary.
  - Geocoding failures and API issues are handled gracefully with friendly messages.

- `backend/app/services/reminder.py`
  - Uses the `dateparser` library to parse natural-language date/time expressions.
  - Exposes:
    - `parse_natural_datetime(text, timezone=...)` → timezone-aware `datetime`.
  - Used by the tool router to turn `SET_REMINDER` `ToolCall`s into concrete timestamps for local notifications.

### Routers

- `backend/app/routers/health.py`
  - `GET /health`
  - Simple health probe used by CI and for manual checks.

- `backend/app/routers/chat.py`
  - `POST /chat`
  - Flow:
    1. Validate `ChatRequest` with Pydantic.
    2. Build a **tool-routing system prompt** via `prompt_builder` that:
       - Describes available tools (weather, reminders, notes, general QA).
       - Defines a strict JSON contract for `ToolCall`.
    3. Ask the LLM to return **only JSON** with:
       - `tool_call`: `{ "name": ..., "args": {...}, "confidence": 0.0-1.0 }`
       - `assistant_message`: optional natural-language reply.
    4. Parse the JSON:
       - If parsing fails, attempt a single \"fix JSON\" retry.
       - If it still fails, fall back to GENERAL_QA without tools.
    5. Execute tools server-side:
       - `WEATHER` → calls Open-Meteo via `weather.py` and returns a grounded summary.
       - `SET_REMINDER` → parses datetime and emits an action:
         - `{\"type\": \"SCHEDULE_LOCAL_NOTIFICATION\", ...}`.
       - `SAVE_NOTE` → emits an action:
         - `{\"type\": \"SAVE_NOTE_LOCAL\", ...}`.
       - `GENERAL_QA` → direct answer via LLM (using the base system prompt).
    6. Return `ChatResponse` with:
       - `reply_text`
       - `debug` (model + latency)
       - `errors` (if any)
       - `actions` (list of client-side actions such as local notifications and notes)
       - `tool_debug` (parsed `ToolCall` and JSON-fix info for debugging).
  - Handles exceptions robustly:
    - Logs detailed errors with `request_id`.
    - Returns friendly, non-leaky error messages to the client.

### Entry Point & Tests

- `backend/app/main.py`
  - Creates the FastAPI application instance.
  - Configures CORS for local dev.
  - Applies logging and middleware.
  - Includes routers.

- `backend/tests/test_health.py`
  - Validates that `/health` returns 200.

- `backend/tests/test_chat_schema.py`
  - Basic validation of chat schema invariants.

---

## Mobile App (`mobile/`)

### Core

- `mobile/lib/core/config.dart`
  - Central place to determine:
    - Backend base URL (e.g., `http://10.0.2.2:8000` for Android emulator).
  - Exposes methods to update base URL (e.g., from `SettingsScreen`).

- `mobile/lib/core/logger.dart`
  - Lightweight wrapper over `debugPrint` / `developer.log`.
  - Provides structured, tagged logging (e.g., `Log.info`, `Log.error`).

- `mobile/lib/core/errors.dart`
  - Defines `AppException` and more specific exceptions:
    - Permission errors, network errors, STT/TTS errors.
  - Used to ensure controllers surface meaningful messages to the UI.

- `mobile/lib/core/storage.dart`
  - Initializes and manages local storage with **Hive**.
  - Persists:
    - Conversation history per `session_id`.
    - Notes created via tool actions.
  - Provides JSON export helpers for conversations.

- `mobile/lib/core/notifications.dart`
  - Wraps `flutter_local_notifications` initialization and scheduling.
  - Schedules reminders locally on the device in response to backend `actions`.

### Assistant Feature (`features/assistant/`)

- `assistant_screen.dart`
  - Main user-facing screen:
    - Large mic button for push-to-talk.
    - Status indicator (Idle / Listening / Thinking / Speaking / Error).
    - Current transcript (partial and final).
    - Latest assistant reply.
    - Simple scrollable chat history list.
  - Displays snackbars or banners for error states (permissions, no speech, backend failures).

- `assistant_controller.dart`
  - `ChangeNotifier` that orchestrates:
    - Mic permissions (`permission_handler`).
    - STT lifecycle (`speech_to_text`).
    - HTTP calls to backend (`assistant_service.dart`).
    - TTS playback (`flutter_tts`).
    - Internal state: status, transcript, response, chat history, and errors.
  - Ensures that all exceptions are logged and converted into user-friendly messages.

- `assistant_models.dart`
  - Data models for:
    - Assistant status enum.
    - Response style enum.
    - Chat message representation (role, content, timestamp).
  - Designed so they can later be shared with persistence layers.

- `assistant_service.dart`
  - HTTP client wrapper (using `http` package) for `/chat`.
  - Builds request payloads that match `context/API_CONTRACT.md`.
  - Parses and validates `reply_text` from the backend.
  - Converts network / protocol issues into domain-specific exceptions.

### Settings Feature (`features/settings/`)

- `settings_screen.dart`
  - UI for:
    - Choosing response style (`concise`, `normal`, `detailed`).
    - Adjusting TTS rate.
    - Editing backend base URL.
  - Communicates changes to controllers and config.

- `settings_controller.dart`
  - Holds current settings state.
  - Notifies listeners and updates:
    - Backend URL in `Config`.
    - Response style in `AssistantController`.
    - TTS rate in `AssistantController`.

---

## CI / Tooling

- GitHub Actions workflow:
  - **Backend job**
    - Install dependencies from `backend/requirements.txt` (or `pyproject.toml` setup).
    - `ruff` linting and format check.
    - `pytest` for backend tests.
  - **Mobile job**
    - Install Flutter (stable channel).
    - `flutter pub get`.
    - `flutter analyze`.
    - `flutter test` (minimal tests).

---

## Extensibility

This component layout is intentionally modular:

- New platforms (e.g., web, desktop) can reuse:
  - Backend API (`/chat`).
  - Context folder for prompts and product description.
- New backend capabilities (e.g., weather, reminders) can be implemented:
  - As new services and routers in `backend/app`.
  - As new features in `mobile/lib/features/`.
- Changes to product direction should primarily be reflected in:
  - `context/GOAL.md`
  - `context/ARCHITECTURE.md`
  - `context/DECISIONS.md`
  - `context/CHANGELOG.md`
and then propagated into code as needed.