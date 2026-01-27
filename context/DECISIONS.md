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

## [D-006] Tool Routing and Actions

- **Date:** 2026-01-27
- **Decision:**
  - The `/chat` endpoint performs **tool routing** using the local LLM:
    - The model returns a strict JSON `ToolCall` plus an optional `assistant_message`.
    - Supported tools: `WEATHER`, `SET_REMINDER`, `SAVE_NOTE`, and `GENERAL_QA`.
  - The backend executes tools where appropriate and returns a final `reply_text` plus a list of `actions` for the client.
- **Rationale:**
  - Keeps all external integrations (weather, reminders, notes) behind a single, typed contract.
  - Allows the mobile client to remain relatively thin: it schedules local notifications and persists notes based on `actions`, without re-implementing NLU.
  - The strict JSON contract and one-shot retry for JSON fixing keep behavior predictable and debuggable.
- **Implications:**
  - `/chat` responses now include:
    - `actions`: structured instructions for the client (e.g., scheduling a local notification).
    - `tool_debug`: optional debug payload with the parsed `ToolCall`.
  - Clients that do not understand actions can ignore them without breaking.
  - Future tools (e.g., weather via other providers, timers, open-meteo-based forecasts) can be added by extending the tool schema and router logic.

---

## [D-007] Open-Meteo for Weather

- **Date:** 2026-01-27
- **Decision:**
  - Use **Open-Meteo** for weather data and geocoding:
    - Geocoding API to resolve city names when coordinates are not provided.
    - Forecast API to fetch current weather for a given lat/lon.
- **Rationale:**
  - Open-Meteo is free, does not require an API key, and is well-suited to the free-first constraint.
  - Combining geocoding + forecast in a single provider simplifies configuration and error handling.
- **Implications:**
  - Weather lookups are performed server-side in the backend and summarized into natural-language responses.
  - If geocoding or weather APIs fail, the backend returns clear, user-friendly fallbacks without breaking the `/chat` contract.
  - The integration remains optional: if Open-Meteo is unreachable, the assistant explains the limitation instead of failing.

---

## [D-008] Local Reminders and Notes

- **Date:** 2026-01-27
- **Decision:**
  - Reminders and notes are handled **locally on the user’s device**:
    - The backend parses reminder times and returns a `SCHEDULE_LOCAL_NOTIFICATION` action.
    - The mobile client uses `flutter_local_notifications` to schedule notifications.
    - Notes are created via `SAVE_NOTE_LOCAL` actions and persisted locally.
  - No remote reminder service or cloud storage is used in V1.
- **Rationale:**
  - Keeps user data on-device, consistent with privacy and free-first goals.
  - Avoids dependency on third-party reminder services or paid APIs.
  - Keeps the backend stateless with respect to user-specific reminders/notes.
- **Implications:**
  - Scheduled reminders are visible only on the device where they were created.
  - Future versions may add:
    - Cross-device sync.
    - A dedicated reminder/notes store with optional cloud backup.
  - Any such evolution must keep the `/chat` `actions` contract backward-compatible or versioned.

---

## [D-009] Local Persistence with Hive

- **Date:** 2026-01-27
- **Decision:**
  - Use **Hive** on the Flutter client to persist:
    - Conversation history per `session_id`.
    - Notes created by the assistant.
  - The backend remains stateless; persistence is purely client-side for V1.
- **Rationale:**
  - Hive is lightweight, free, and does not require native schema migrations for simple use cases.
  - Aligns with the goal of local, offline-friendly operation without paid services.
- **Implications:**
  - Conversation history and notes survive app restarts on a given device.
  - Export of conversations as JSON is straightforward (Hive → JSON string → clipboard or file).
  - Future sync or backup layers can be built on top of this local storage without changing the `/chat` contract.

---

## [D-010] Dual Free Deployment Paths (HF LlamaCpp + Cloudflare Tunnel)

- **Date:** 2026-01-27
- **Decision:**
  - Provide two official, free deployment paths for the backend:
    - **HF Spaces + LlamaCpp (demo mode):**
      - Use a CPU-only TinyLlama GGUF model via `llama-cpp-python`.
      - Configure with `LLM_PROVIDER=llamacpp`.
    - **Local backend + Cloudflare tunnel (best experience):**
      - Run Ollama + backend locally (`LLM_PROVIDER=ollama`).
      - Expose `/chat` publicly via a temporary Cloudflare tunnel URL.
  - Introduce `LLM_PROVIDER` and LlamaCpp-specific settings in backend config:
    - `LLM_PROVIDER` (default `ollama`).
    - `LLAMACPP_MODEL_REPO`, `LLAMACPP_MODEL_FILE`, `LLAMACPP_CONTEXT_LENGTH`, `LLAMACPP_MAX_TOKENS`.
- **Rationale:**
  - HF CPU Spaces cannot reliably run Ollama in a free, GPU-accelerated way.
  - A tiny GGUF model provides a **fully free**, container-friendly demo path without adding paid SaaS dependencies.
  - Cloudflare Tunnel allows users to keep the **full-quality local Ollama setup** while sharing it temporarily with phones or remote devices.
  - The `LLM_PROVIDER` switch keeps configuration explicit and easy to reason about.
- **Implications:**
  - The backend now has two local LLM backends behind a single `/chat` API:
    - Ollama for local-first usage.
    - LlamaCpp TinyLlama for constrained/demo environments.
  - HF Spaces deployments should:
    - Set `LLM_PROVIDER=llamacpp`.
    - Expect slower cold starts while the TinyLlama model downloads and initializes.
    - Surface “demo degraded” messages instead of raw 500s when the model fails.
  - Local deployments remain unchanged by default (`LLM_PROVIDER=ollama`), preserving the free-first, local-first behavior.
  - New environment variables must be documented and kept in sync across:
    - `backend/.env.example`
    - `context/ARCHITECTURE.md`
    - `context/COMPONENTS.md`
    - `context/DEPLOY_FREE.md`.

---

When making new decisions:

1. Add a new section with an ID `[D-XXX]`.
2. Clearly state the decision, rationale, and implications.
3. Cross-link to relevant sections in `GOAL.md`, `ARCHITECTURE.md`, and `API_CONTRACT.md` where appropriate.