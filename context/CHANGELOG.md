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