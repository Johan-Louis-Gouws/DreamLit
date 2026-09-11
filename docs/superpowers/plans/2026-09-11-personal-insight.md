# Personal insight implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement the tasks with scoped reviews. Work in the current workspace as authorised by the specification; do not stage existing untracked files or commit changes.

**Goal:** Add the six selected personal-insight features as connected, persistent and source-backed workflows.

**Architecture:** Keep the SQLite/React/CLI architecture. A focused insights package stores versioned personal records, selects and validates source-backed generation, and supplies context to existing analysis. Three new frontend views share citations, jobs, and record editors.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, SQLite, React 19, TypeScript, existing CLI adapters and local whisper.cpp.

**Spec:** `docs/superpowers/specs/2026-09-11-personal-insight-design.md`

## Global constraints

- Preserve journal content and existing features; use temporary synthetic journals for testing.
- Keep primary storage local and provider calls explicit; no fallback provider, automation, email, or new hosted service.
- Preserve original user statements, validate citations, propagate edits/deletions, and exclude changed/excluded context from future inference.
- Keep six features, with relationships nested in Your World, investigations in Explore, and experiments/letters in Review.
- Use the exact record, source, output and endpoint contracts in the specification.

## Task 1: Personal records, runs persistence, and REST API

**Files:** Create `backend/dreamlit/insights/__init__.py`, `records.py`, `store.py`, `schema.sql`, `api.py`; modify `storage.py`, `api.py`, `export.py`; create `tests/test_insight_records.py`.

**Interfaces:** Implements all InsightStore methods and record models in the spec; API enqueues `insight` jobs without owning generation. Existing Store.save_analysis accepts optional personal_context and records personal dependencies.

- [ ] Write behavioral tests: POST an answer, revise it with expected_revision=1, confirm original remains in `/history`, reject a second revision with stale expected_revision=1, exclude it and confirm `InsightStore.sources()` omits it. Verify bad person links return 422 and deletion clears links. Verify source edit invalidates and deletion removes dependent runs and analyses. Verify new data is exported.
- [ ] Run `.venv/bin/python -m pytest tests/test_insight_records.py -q` and observe the missing API/storage failure.
- [ ] Implement typed payload validation, versioned CRUD, source conversion, transactional run saving and invalidation. Initialise new schema on existing Store startup. Register the router with create_app; use request.app.state.store/runner and return the established public Job shape. Avoid importing generation code into routes.
- [ ] Run the new tests plus journal/lifecycle/API tests and fix failures within this task's files.

## Task 2: Source selection, generation, and existing-analysis context

**Files:** Create `backend/dreamlit/insights/generation.py`, `sources.py`, `outputs.py`; modify `models.py`, `jobs.py`, `analysis/context.py`, `analysis/service.py`, `analysis/scan.py`, `analysis/prompts.py`; create `tests/test_insight_generation.py` and extend deterministic `tests/test_api.py` provider.

**Interfaces:** Consumes InsightStore. Produces async `generate_insight(store,providers,payload,provider,job_id,job_dir)` and bounded `personal_context(store)` for existing ContextSnapshot.personal_context. Provider task names are `insight_question`, `insight_turning_points`, `insight_investigation`, `insight_portrait`, `insight_weekly`; payload includes `sources` and `scope`.

- [ ] Add provider-fixture tests for each run kind; bad quote/wrong revision, empty history, date filtering, excluded context, unrelated person name substrings, failed generation, and editing a source during a request.
- [ ] Run `.venv/bin/python -m pytest tests/test_insight_generation.py -q` to establish failing behavior.
- [ ] Implement kind-specific instructions, complete-source budget selection, typed outputs and exact citation validation; distinguish user records from dream passages and hypotheses. Reuse provider request preferences, queue cancellation and existing failure handling. Include context in every existing analysis path and pass context dependencies when saving analyses.
- [ ] Run focused generation/context/evidence/scan/job tests.

## Task 3: Six-feature frontend experience

**Files:** Create `frontend/src/features/insights/{types.ts,shared.tsx,YourWorld.tsx,People.tsx,Explore.tsx,Review.tsx,insights.css}` (split additional focused components if useful); modify `App.tsx`, `features/reflection/ReflectionPanel.tsx`, `features/diary/DreamDetail.tsx`; create `frontend/tests/insights.spec.ts`.

**Interfaces:** Uses specified records/runs endpoints and existing api/json, JobProgress, DreamDetail source navigation. Answer voice input uses standalone `AnswerVoice` supplied by Task 4. Generation results use the exact InsightOutput/InsightSource contracts.

- [ ] Write browser tests for a user saving/editing/excluding an answer, creating a person and portrait, comparing two dreams, starting and resolving an investigation, recording/completing an experiment, generating a weekly letter, and opening a citation. Test phone navigation and horizontal overflow.
- [ ] Build Your World with starter topics, generated questions, current/changed/excluded states and original history; People with aliases/context and source-backed portrait; Explore with turning-point evidence and persistent investigations; Review with experiment outcomes and dated weekly letters. Supply empty/error/loading states and explicit generation actions. Add the new nav entries while retaining existing routes and brand styles.
- [ ] Add a deliberate Save as context action for user reflection replies, preserving the original prompt. Show personal context provenance in dream analyses. Refresh views after edits and generation; mark invalidated output stale and offer regeneration.
- [ ] Run `npm --prefix frontend run build` and `npm --prefix frontend run test:e2e -- insights.spec.ts` after integration with deterministic provider support.

## Task 4: Voice, integration, and final verification

**Files:** Create `backend/dreamlit/insights/voice.py`, `frontend/src/features/insights/AnswerVoice.tsx`, `tests/test_insight_voice.py`; modify `audio.py`, `jobs.py`, route registration as needed; update README and this plan.

**Interfaces:** POST multipart `/api/insights/voice` saves original audio and enqueues `insight_transcription`. GET `/api/insights/voice/:id` returns audio_id,text,state/job. AnswerVoice accepts onAccept(text,audio_id), keeps original recording playback, and explicitly inserts only reviewed text into an answer. No artificial dream entries are created.

- [ ] Test preserved recordings and no new dreams on voice upload; failed local transcription leaves audio usable; transcript is reviewed before any answer or analysis save.
- [ ] Extract the existing local transcription process into reusable audio-to-text logic if needed, keeping current dream voice behavior intact. Add the standalone transcript storage/route and frontend recorder/import controls.
- [ ] Run `.venv/bin/python -m pytest`, `.venv/bin/python -m ruff check backend tests scripts`, frontend build and full browser tests. Resolve new failures and re-run the affected checks.
- [ ] Inspect actual desktop/phone views with the browser skill using a temporary journal. Review all new source/deletion/context paths and repair material issues.
- [ ] Update README usage and report verified behavior and limitations. Keep existing personal data unchanged.

## Preflight and progress

Task 1 owns the store and API, Task 2 owns generation and job integration, Task 3 owns navigation and feature UI, Task 4 owns voice. Contracts are shared through the spec. Task 1 and Task 2 can be developed by one worker and the root respectively; Task 3 follows the persistence/API contract. Only one implementation subagent runs at a time. The root handles integration and verification alongside disjoint work.

Ruling: user selection approves implementation of the six described features. Record further reversible decisions here and continue without repeating approval questions.
