# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Dates are in `YYYY-MM-DD` format.

---

## [0.1.0] - 2026-01-26

### Added

- Initial repository scaffolding for **Jarvis Voice Agent V1**:
  - Root `README.md` and `.gitignore`.
  - `context/` folder with:
    - `GOAL.md` – product goals, scope, free-first constraints, and DoD.
    - `ARCHITECTURE.md` – high-level architecture and voice loop sequence diagram.
    - `COMPONENTS.md` – description of backend/mobile components.
    - `API_CONTRACT.md` – canonical `/chat` request/response schema.
    - `COSINE_GROUNDING.md` – guidance for future Cosine tasks and change discipline.
    - `DECISIONS.md` – initial architecture and product decisions.
    - `CHANGELOG.md` – this file.
  - Backend structure:
    - FastAPI app with `main.py`, `core`, `schemas`, `services`, `routers`.
    - Health and chat endpoints.
    - Ollama client and prompt builder.
    - Centralized config and logging.
    - Minimal tests (`test_health.py`, `test_chat_schema.py`).
    - `requirements.txt` and `.env.example`.
  - Mobile (Flutter) structure:
    - `pubspec.yaml` with dependencies for STT, TTS, HTTP, permissions, and state management.
    - Core modules (`config.dart`, `logger.dart`, `errors.dart`).
    - Assistant feature (`assistant_screen.dart`, `assistant_controller.dart`, `assistant_models.dart`, `assistant_service.dart`).
    - Settings feature (`settings_screen.dart`, `settings_controller.dart`).
    - Placeholder `android/` and `ios/` directories for platform projects.

- Basic CI workflow:
  - Backend:
    - Install dependencies.
    - Run `ruff` linting and format checks.
    - Run `pytest` tests.
  - Flutter:
    - Run `flutter pub get`.
    - Run `flutter analyze`.
    - Run `flutter test` (minimal test suite).

### Notes

- No secrets are committed; only `.env.example` is included.
- Conversation history is in-memory only on the client for this version.
- `/chat` includes a fallback reply mechanism when Ollama is unavailable.

---

## [0.2.0] - 2026-01-27

### Added

- **Tool routing** in `/chat`:
  - Strict `ToolCall` schema with tools:
    - `WEATHER`, `SET_REMINDER`, `SAVE_NOTE`, `GENERAL_QA`.
  - LLM instructed to output only JSON:
    - `{"tool_call": {...}, "assistant_message": "..."}`.
  - Robust JSON parsing with a single "fix JSON" retry before falling back to GENERAL_QA.
  - Weather integration via **Open-Meteo**:
    - Optional geocoding for city names.
    - Current weather summaries returned as grounded natural language.
  - Reminder handling:
    - Natural-language datetime parsing using `dateparser`.
    - Emission of `SCHEDULE_LOCAL_NOTIFICATION` actions.
  - Notes handling:
    - Emission of `SAVE_NOTE_LOCAL` actions.

- **Extended `/chat` response contract**:
  - New `actions` array for client-side actions (local notifications, notes).
  - New `tool_debug` object for tool call inspection and JSON-fix hints.
  - Backward-compatible defaults for existing clients.

- **Backend services and tests**:
  - `backend/app/services/weather.py` with geocoding + forecast helpers.
  - `backend/app/services/reminder.py` for parsing reminder times.
  - Additional tests:
    - `test_tool_schemas.py` – validates ToolCall/ToolRouterResult schemas.
    - `test_reminder_service.py` – tests reminder parsing behavior.
    - `test_weather_summary.py` – tests weather summary formatting.

- **Mobile persistence and actions**:
  - Hive-based local storage (`Storage`):
    - Conversation history persisted per `session_id`.
    - Notes persisted locally.
  - Local notifications (`NotificationService`) using `flutter_local_notifications`.
  - Assistant controller:
    - Handles backend `actions`:
      - Schedules local notifications.
      - Saves notes locally.
    - Reloads persisted conversations on startup.
    - Adds "Export chat as JSON" functionality (copies JSON to clipboard).

- **NLU notebook and dataset utilities**:
  - `notebooks/intent_eda_and_baseline.ipynb`:
    - EDA on intent data.
    - Baseline TF-IDF + Logistic Regression model.
    - Metrics (accuracy, macro F1), confusion matrix, feature importance.
  - `notebooks/README.md` with instructions and rationale.
  - `scripts/download_intent_dataset.py` to fetch CLINC OOS data (optional).
  - `data/sample_intents.csv` for offline, minimal experiments.
  - `requirements-notebook.txt` with notebook-specific dependencies (kept separate from backend runtime).

- **Deployment artifacts**:
  - `backend/Dockerfile` for containerizing the FastAPI backend (HF Spaces compatible).
  - `backend/README_DEPLOY.md` – backend-focused deployment guide.
  - Root `DEPLOYMENT.md` – high-level deployment options (local + Docker/HF Spaces).

### Notes

- All new external integrations (Open-Meteo, CLINC OOS via `datasets`) are **free-first** and optional.
- The default running mode still assumes a local Ollama instance and local-only operation.
- No secrets were added; configuration continues to use environment variables and `.env.example`.

---

## [0.3.0] - 2026-01-27

### Added

- **Developer runbooks:**
  - `context/RUN_LOCAL.md`:
    - End-to-end local setup instructions (Git, Python, Flutter, Android Studio, Xcode, Ollama).
    - Bash / PowerShell / `make` variants for:
      - Creating a backend virtualenv.
      - Installing backend dependencies.
      - Copying `backend/.env.example` → `backend/.env`.
      - Running the backend on `0.0.0.0:8000`.
      - Running the Flutter app on Android emulator, iOS simulator, and physical devices.
    - Troubleshooting for:
      - Ollama connectivity.
      - CORS issues.
      - Emulator localhost quirks.
      - STT “no speech recognized”.
      - Port conflicts.
  - `context/DEPLOY_FREE.md`:
    - **Path 1 – Hugging Face Spaces (Docker + LlamaCpp TinyLlama demo):**
      - Explains CPU/container constraints with Ollama.
      - Documents `LLM_PROVIDER=llamacpp` and TinyLlama GGUF defaults.
      - Step-by-step Space creation (Docker SDK, `app_port: 7860`, env vars, logs).
    - **Path 2 – Local backend + Cloudflare Tunnel:**
      - Run Ollama + backend locally; expose via `cloudflared tunnel --url http://localhost:8000`.
      - Configure the mobile app to use the HTTPS tunnel URL.
    - **Mobile distribution (free):**
      - `flutter build apk --release` and GitHub Releases for Android.
      - iOS simulator + screen recording for free demos.

- **Pluggable LLM provider configuration:**
  - New `LLM_PROVIDER` env var with values:
    - `ollama` (default, local-first).
    - `llamacpp` (TinyLlama GGUF demo mode).
  - New backend settings and env vars:
    - `LLAMACPP_MODEL_REPO`, `LLAMACPP_MODEL_FILE`.
    - `LLAMACPP_CONTEXT_LENGTH`, `LLAMACPP_MAX_TOKENS`.
  - `backend/app/core/config.py`:
    - Validates `LLM_PROVIDER` and LlamaCpp numeric settings.
    - Adds `debug_model_name` for consistent `/chat.debug.model` values.

- **LlamaCpp TinyLlama provider:**
  - `backend/app/services/llamacpp_client.py`:
    - Downloads TinyLlama GGUF from Hugging Face using `huggingface_hub.hf_hub_download`.
    - Loads the model with `llama-cpp-python` and a moderate context window.
    - Provides an async `chat(messages)` API mirroring the Ollama client.
    - Logs clear “model ready” messages and wraps errors in typed exceptions.
  - `backend/app/main.py`:
    - On startup, warms up the LlamaCpp model when `LLM_PROVIDER=llamacpp`, logging failures without crashing the app.

- **`/chat` router provider abstraction:**
  - `backend/app/routers/chat.py`:
    - Introduces `_provider_chat` helper to route calls to either Ollama or LlamaCpp based on `LLM_PROVIDER`.
    - Extends error handling to:
      - Distinguish between Ollama-specific errors (`ollama_connection_error`) and generic LLM provider issues (`llm_provider_error`).
      - Return friendly “demo degraded” messages when TinyLlama cannot be used.
    - Uses `settings.debug_model_name` for `debug.model` to reflect the active provider.

- **Tooling & dev experience:**
  - Root `Makefile` with targets:
    - `backend-venv`, `backend-install`, `backend-dev`, `backend-test`.
    - `mobile-get`, `mobile-run-android`.
    - `format`, `lint` (backend + Flutter analyze).
  - New helper scripts in `scripts/`:
    - `dev.sh` / `dev.ps1`:
      - Check Ollama health.
      - Start the backend on `0.0.0.0:8000` and print useful URLs.
    - `backend-dev.sh` / `backend-dev.ps1`:
      - Create/activate `backend/.venv`, install deps, run uvicorn with reload.
    - `mobile-run.sh` / `mobile-run.ps1`:
      - Run `flutter pub get` and `flutter run` in `mobile/`.

- **Configuration & docs sync:**
  - Added `backend/.env.example` including:
    - `LLM_PROVIDER`, `OLLAMA_*`, `LLAMACPP_*`, `REQUEST_TIMEOUT_S`, `CORS_ALLOW_ORIGINS`.
  - Updated context docs:
    - `context/ARCHITECTURE.md` and `context/COMPONENTS.md` to describe LLM providers and new env vars.
    - `context/API_CONTRACT.md` to clarify `debug.model` semantics and new `llm_provider_error` code.
    - `context/DECISIONS.md` with `[D-010]` documenting the dual free deployment paths.
  - Updated deployment docs:
    - `backend/README_DEPLOY.md` and root `DEPLOYMENT.md` to reference `LLM_PROVIDER` and `context/DEPLOY_FREE.md`.
    - Root `README.md` to link to the new runbooks.

### Notes

- All new dependencies (`llama-cpp-python`, `huggingface_hub`) are used only for the optional LlamaCpp provider and keep to the free-first constraint.
- Default behavior (`LLM_PROVIDER=ollama`) preserves the original local-only Ollama architecture.
- No secrets were added; configuration continues to use environment variables and `.env.example` only.