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
  - Robust JSON parsing with a single \"fix JSON\" retry before falling back to GENERAL_QA.
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
    - Adds \"Export chat as JSON\" functionality (copies JSON to clipboard).

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