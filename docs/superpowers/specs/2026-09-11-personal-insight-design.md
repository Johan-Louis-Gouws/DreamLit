# DreamLit personal insight features

Date: 2026-09-11
Scope approved: the user selected Your World, Turning Points, Investigate This, Relationship Portraits, Small Experiments, and the Weekly Letter from the preceding feature proposals and asked to implement them.

## Product flow

Keep Capture, Diary, and Connections. Add Your World (Questions and People), Explore (Turning Points and Investigations), and Review (Experiments and Weekly Letter). Preserve the existing quiet cream, plum, serif visual language, accessible forms, and phone layouts.

Your World offers a short set of optional starter questions and an explicit request for a tailored next question. Save the original question, answer, topic, date, scope, and optional person/dream link. Questions never block dream capture. Answers can be edited, marked changed, excluded from analysis, reviewed in their original versions, or deleted. Accept text and reuse local voice transcription with an explicit transcript review. Existing reflection replies can be deliberately saved as context; model interpretations are never automatically stored as user facts.

People contains user-maintained names, aliases, relationship descriptions, and personal notes. Generate a portrait of the user's experience using matching dream passages and their own context. Do not infer the other person's actual intentions. Turning Points compares dated dream situations and responses, citing earlier and later passages; no change is a valid result.

Investigations save a user's question, notes, optional linked dreams, status, and conclusion. An explicit investigation looks for supporting examples, counterexamples, alternatives, and one open question. Users can revise, resolve, reopen, or archive their inquiry.

Experiments save a user-chosen action, intention, optional investigation/person, optional check-in date, status, and outcome. Support completing, dropping, and revising experiments. They are reflection records, with no causal claims about later dreams. Weekly Letter summarises a selected seven-day period with a recurrence, a change or exception when supported, and one open question. Include positive experiences. Generate explicitly inside the app; this feature does not create a Codex automation or send messages. Thin evidence should produce a modest reflection, not a fabricated pattern.

## Shared contracts

Use the existing SQLite journal and CLI provider job queue. No new service, hosted account, or dependency is required. Original journal records must survive provider failure, cancellation, or restart. Explicit Generate actions use the selected provider and show progress/retry errors; never silently switch providers.

New package: `backend/dreamlit/insights`. Record persistence and HTTP routes, source selection and generation, and frontend feature views have separate responsibilities.

Record REST API at `/api/insights/records`:

```ts
type RecordKind = 'answer' | 'person' | 'investigation' | 'experiment';
type InsightRecord = {id:string; kind:RecordKind; revision:number; data:Record<string,unknown>; created_at:string; updated_at:string};
// GET ?kind=..., POST {kind,data}, GET /:id,
// PUT /:id {expected_revision,data}, DELETE /:id, GET /:id/history.
// history returns the same record shape for each revision, newest first.
```

Data models (all strings trimmed; meaningful primary fields cannot be blank):

- answer: `question`, `answer`, `topic` (default General), `scope` ongoing/current/dream (default current), `status` current/changed/excluded (default current), `dream_id`, `person_id`, `audio_id` (nullable).
- person: `name`, `aliases` string array (default empty), `relationship` and `notes` (default empty), `include_in_analysis` (default true).
- investigation: `question`, `notes` and `conclusion` (default empty), `status` open/resolved/archived (default open), `dream_ids` (default empty).
- experiment: `action`, `intention` and `outcome` (default empty), `due_on` ISO date or null, `status` planned/active/completed/dropped (default planned), `investigation_id`, `person_id` (nullable).

Validate linked IDs against their required kinds. Record revisions are immutable and stale writes return 409. Deleting a linked record clears live links in a new revision and removes generated output dependent on the deleted source. Do not turn prior model summaries into user records.

Source contract:

```ts
type InsightSource = {kind:'dream'|RecordKind; id:string; revision:number; date:string; label:string; fields:Record<string,string>};
type InsightEvidence = {source_kind:InsightSource['kind']; source_id:string; revision:number; field:string; quote:string};
type InsightOutput = {title:string; summary:string; sections:{heading:string; body:string; evidence:InsightEvidence[]; counterevidence:InsightEvidence[]}[]; question:string};
type RunKind = 'question'|'turning_points'|'investigation'|'portrait'|'weekly';
// POST /api/insights/runs {kind,provider,subject_id?,date_from?,date_to?} -> existing Job.
// GET /api/insights/runs?kind=...&subject_id=..., GET /api/insights/runs/:id.
// Run response: id,kind,subject_id,provider,model,output,sources,scope,stale,created_at.
// scope: included_dream_ids,total_eligible_dreams,truncated,date_from,date_to.
```

Select complete sources within a 60,000-character serialized budget, prioritising the chosen subject, linked dreams/people, and relevant words. World answers with changed/excluded status and excluded people must not be supplied. Portrait matching uses names/aliases with token boundaries and user-linked answers, avoiding substring matches. Weekly dream dates are bounded to the requested seven days; background context can be older and must be identified as background. Context dates and source kinds remain explicit. Display scope and supporting source quotations alongside output.

Validate all quotations against selected source IDs, revisions, fields, and exact text. Turning-point sections require at least two distinct dream sources. Changes during a job must prevent saving a current-looking result. Source edits mark dependent results stale; deletions remove dependent results. Track both dream and personal-context dependencies for existing analyses as well as new runs. Existing extraction, connections, reflections, and history scans receive a bounded set of eligible personal context.

## Persistence interfaces

`InsightStore(store)` uses the existing Store connection and exposes `create_record(kind,data)`, `get_record(id)`, `list_records(kind=None)`, `update_record(id,expected_revision,data)`, `delete_record(id)`, `record_history(id)`, `sources()`, `save_run(kind,subject_id,provider,model,output,sources,scope)`, `get_run(id)`, and `list_runs(kind=None,subject_id=None)`.

`sources()` returns eligible current personal records using the source contract. `save_run` accepts JSON-serializable dicts and atomically checks source revisions. Store initialization creates the new package schema with additive tables. Existing `Store.save_analysis` gains optional `personal_context=None`, storing dependencies and exposing `personal_context_sources` on returned analyses. Export includes all new current records, revisions, generated runs, and source metadata.

`generate_insight(store,providers,payload,provider,job_id,job_dir)` returns the saved run ID. Job kind is `insight`; payload has kind/subject_id/date_from/date_to. The root job runner calls this function. API routes reject missing or wrong-kind subjects and reversed date ranges before enqueueing. An empty journal can still save answers, people, investigations, and experiments without contacting a provider.

## Verification

Use temporary journals and deterministic providers for behavioral tests. Cover record persistence/revisions and exclusions, linked-record validation/deletion, source quotation rejection, source changes during generation, old-analysis context propagation, provider failure/cancellation, scope limits, all five generation kinds, exports, and voice transcript review. Browser tests cover completing the six-feature flow, opening citations, persistent editing, stale notices, and phone layout. Build the frontend and run the existing tests and lint. Browser-inspect desktop and phone views before completion.

## Execution decisions

The user has approved the described feature direction and explicitly requested implementation. Proceed with these reversible local implementation choices without another approval round. The app implementation is currently untracked; retain the working directory and do not stage or commit the user's existing files as a side effect. Work through the dependencies with focused file ownership and verify the combined result.
