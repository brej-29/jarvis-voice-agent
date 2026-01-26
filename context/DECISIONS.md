# Decisions (ADR Log)

This file records key decisions for the Jarvis Voice Agent project. Each entry should answer:

- **What** was decided?
- **Why** was it decided that way?
- **When** was it decided?
- **What are the implications?**

---

## [D-001] Free-First, Local-First Architecture

- **Date:** 2026-01-26
- **Decision:**
  - The system will prioritize **free** and **local** components:
    - STT and TTS use device/OS capabilities via Flutter packages.
    - LLM inference uses a locally running Ollama instance.
    - No required paid cloud APIs for the core voice loop.
- **Rationale:**
  - Users should be able to run Jarvis without recurring costs.
  - Local processing improves privacy and reduces latency.
  - Ollama and platform-native STT/TTS offer a good balance between quality and cost.
- **Implications:**
  - Network and performance constraints are mostly local; the backend assumes Ollama is on `localhost` by default.
  - Any future cloud integrations must be optional and degrade gracefully.
  - Prompt builder and system design assume a single local LLM, not a multi-tenant cloud service.

---

## [D-002] Backend as a Thin, Typed API over Ollama

- **Date:** 2026-01-26
- **Decision:**
  - Implement a **FastAPI backend** that:
    - Exposes `/health` and `/chat` endpoints.
    - Uses strong Pydantic schemas around the `/chat` contract.
    - Forwards requests to Ollama `/api/chat` with minimal extra logic (plus a thin system prompt and retries).
- **Rationale:**
  - FastAPI provides good developer ergonomics, validation, and async IO.
  - A thin API keeps initial complexity low while still giving a stable contract to mobile clients.
  - Pydantic schemas catch malformed requests early and document the contract.
- **Implications:**
  - The backend is stateless with respect to conversations in V1.
  - Conversation continuity is driven by the client carrying `messages` in each request.
  - Future skills (e.g., tools, weather, reminders) can be added as new routers/services.

---

## [D-003] Flutter as the Primary Client

- **Date:** 2026-01-26
- **Decision:**
  - Use **Flutter** as the primary client for V1:
    - Mobile-focused (Android/iOS).
    - Voice interaction as a first-class citizen (push-to-talk).
    - State managed via `ChangeNotifier` + `provider` (lightweight but structured).
- **Rationale:**
  - Flutter provides a strong cross-platform story for mobile.
  - `speech_to_text` and `flutter_tts` are well-supported Flutter plugins for STT/TTS.
  - `provider` is simple, widely used, and sufficient for early versions.
- **Implications:**
  - `AssistantScreen` and `SettingsScreen` become canonical UX surfaces for V1.
  - Future web/desktop clients can reuse the same backend API and adapt the architecture as needed.

---

## [D-004] Context-Driven Prompting

- **Date:** 2026-01-26
- **Decision:**
  - The system prompt sent to Ollama is derived from curated excerpts of:
    - `context/GOAL.md`
    - `context/COMPONENTS.md`
  - Prompt builder is responsible for:
    - Minimizing token usage.
    - Reflecting the latest project intent.
- **Rationale:**
  - Keeps prompt logic aligned with documented goals and architecture.
  - Avoids hard-coding product decisions directly in code.
  - Makes it easier for future agents to adjust behavior by editing context files.
- **Implications:**
  - Updating product behavior requires updating context documents and `prompt_builder`.
  - Prompt content should be periodically reviewed as the project evolves.

---

## [D-005] In-Memory Conversation History (Phase 1)

- **Date:** 2026-01-26
- **Decision:**
  - In V1, conversation history is stored **locally in memory** on the device/app only.
  - No persistent storage or cloud sync is implemented yet.
- **Rationale:**
  - Keeps initial complexity low.
  - Allows focusing on end-to-end voice loop stability.
  - Architecture can be extended later to add persistence and sync without breaking the `/chat` API.
- **Implications:**
  - Conversation history is lost when the app is closed or restarted.
  - Future tasks will introduce a storage abstraction (e.g., local database) and optional sync without changing the `/chat` contract.

---

When making new decisions:

1. Add a new section with an ID `[D-XXX]`.
2. Clearly state the decision, rationale, and implications.
3. Cross-link to relevant sections in `GOAL.md`, `ARCHITECTURE.md`, and `API_CONTRACT.md` where appropriate.