# Cosine Grounding & Change Discipline

This document explains how future **Cosine tasks** and **AI agents** should use the `context/` folder as the primary source of truth for the Jarvis Voice Agent.

---

## Purpose of the `context/` Folder

The `context/` folder exists so that:

- Humans and AI agents can quickly understand **what this project is**, **how it should behave**, and **why certain decisions were made**.
- Prompt builders and backend logic can pull small, curated excerpts from these files to **ground the language model** in the intended product behavior.
- Changes to the system are **documented explicitly**, not inferred from scattered code comments.

In other words: **start with `context/` before touching code.**

---

## How Future Cosine Tasks Should Use This Context

When working on new tasks, agents should:

1. **Read these files first:**
   - `GOAL.md` – understand the product vision, V1 vs V2 scope, and free-first constraints.
   - `ARCHITECTURE.md` – understand the main data flow and components.
   - `API_CONTRACT.md` – understand the `/chat` request/response shape.
   - `DECISIONS.md` – understand the important trade-offs and why they were made.
   - `CHANGELOG.md` – understand what changed recently and whether similar work was done.

2. **Treat them as canonical.**
   - If code appears to conflict with `context/`, assume:
     - The context is correct and the code has drifted, or
     - The change was made without updating the context (which is a process violation to fix).

3. **Only change behavior when context is updated accordingly.**
   - If a task requires changing how the system behaves, **update the relevant context files as part of the same change**.

4. **Keep prompt builder aligned with context.**
   - `backend/app/services/prompt_builder.py` should pull from `GOAL.md`, `COMPONENTS.md`, and possibly other context files.
   - If you update product intent or system responsibilities, revisit the prompt builder to ensure it still reflects the new reality.

---

## Change Discipline

Whenever a behavioral or architectural change is introduced, follow this discipline:

1. **Update `DECISIONS.md`**
   - Add a new decision entry with:
     - A clear title.
     - The date.
     - The decision.
     - The rationale and any trade-offs.
     - The scope (what parts of the system it affects).

2. **Update `CHANGELOG.md`**
   - Add an entry describing:
     - What changed (from a user and developer perspective).
     - Whether the change is backward compatible.
     - Any migrations or configuration adjustments required.

3. **Update other context files as needed**
   - `GOAL.md` – when product goals or scope change.
   - `ARCHITECTURE.md` – when data flow, components, or responsibilities change.
   - `API_CONTRACT.md` – when any part of the `/chat` API behavior or shape changes.

4. **Then update the code**
   - Once the context reflects the desired change, update the backend/mobile code to match.
   - Ensure tests and CI reflect new behavior where applicable.

---

## Grounding for LLM Prompts

The backend uses a **prompt builder** that reads small excerpts from `GOAL.md` and `COMPONENTS.md` to generate a system prompt for the local LLM. The goals:

- **Stay minimal** – only short excerpts to avoid token bloat and latency.
- **Stay accurate** – always pull from the same canonical context files.
- **Stay aligned** – update these context files before changing prompt behavior.

Future prompt improvements (e.g., skill-specific instructions, safety guidelines, or user preferences) should be made by:

1. Updating or adding context files.
2. Adjusting `prompt_builder` to incorporate the relevant new context in a controlled, size-bounded way.

---

## Summary

- `context/` is the **source of truth** for:
  - What this project is trying to achieve.
  - How it is architected.
  - Which decisions were made and why.
  - How the `/chat` API behaves.
- **Change discipline**:
  - Update `DECISIONS.md` and `CHANGELOG.md` (and other context files) whenever behavior changes.
  - Only then adjust code and prompts to match.
- Future Cosine tasks and AI agents should **always read and respect these files** before making changes.