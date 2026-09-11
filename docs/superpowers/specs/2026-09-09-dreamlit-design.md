# DreamLit: local web app with CLI-powered dream analysis

Date: 2026-09-09
Status: Approved by the user on 2026-09-09; implementation planning in progress.

## Product purpose

Help a person recognise recurring emotional situations across dreams whose surface stories appear unrelated. The desired experience is a surprising, personally useful connection supported by the person's own entries. Characters, places, emotions, and narrative relationships should become visible over time.

The user wants the app to address uncomfortable possibilities directly, including possible avoidance. The app must distinguish an observed recurrence from a proposed explanation. Its tone can be blunt without claiming knowledge that the entries do not establish.

## Confirmed direction

- First version is a web app started on the user's computer and opened in a browser.
- Capture dreams through a written diary or a voice note, with minimal effort after waking.
- Use Codex CLI and Claude CLI to power the app's analysis in the initial version.
- Integrate provider APIs later, when developing the polished app.
- Use a very direct reflection style.

The latest CLI requirement replaces the earlier proposal to use Ollama for entirely on-device language-model inference. The interpretation here is that the CLIs are runtime analysis engines, as well as tools that may be used to develop the app.

With ordinary hosted Codex and Claude configurations, the interface and primary journal database run locally while the selected CLI sends analysis content to its provider. The app must describe this accurately. Selecting a second provider also sends the selected analysis context to that provider. Local journal storage is not a promise of offline inference or exclusive local copies.

## Approved first-version scope

A single-person journal with four connected views:

1. Capture: write, record, or import an audio note; save the original immediately.
2. Diary: browse and search dated entries, play recordings, correct transcripts, and add optional context.
3. Connections: explore dreams, recurring entities, and emotional situations through an interactive constellation.
4. Reflection: inspect the evidence behind a pattern and discuss it with the selected CLI engine.

Include editing, deletion, and export of the local journal. Use an optional short waking-life note and personal associations to enrich context. Do not require a questionnaire before saving a dream. Accounts, hosted deployment, subscriptions, social sharing, and automatic interpretation of other people's intentions are outside this version.

## CLI approaches and recommendation

| Approach | Behaviour | Trade-off |
| --- | --- | --- |
| Selectable engine with optional second opinion — recommended | Both CLIs are integrated. Use one selected engine for a normal analysis; explicitly request the other when useful. | A simple baseline with controlled latency and provider usage. A second opinion remains available. |
| Analyst followed by critic | One CLI proposes patterns; the other reviews the evidence and alternatives for every analysis. | Additional latency and usage; disagreement needs a clear presentation. |
| Two independent analyses | Each CLI sees the same source entries before seeing the other's output. | Useful for comparison experiments, but produces more material to reconcile. |

These are product options, not claims that either model is inherently better at dream interpretation. Agreement between models is not scientific validation.

Use the approved selectable-engine approach, with Codex initially selected and Claude equally available. Preserve each CLI's configured model unless the user chooses an override. Do not automatically switch providers on failure. A second opinion is labelled with its provider and does not overwrite the first analysis.

## Runtime architecture

Use a browser frontend, a small local backend, SQLite for structured records, and a local directory for audio. React with TypeScript and a Python backend are proposed implementation choices, subject to the implementation plan. Bind the service to loopback for the first version.

The backend owns persistence, context selection, jobs, and result validation. It invokes Codex or Claude as a subprocess behind the same analysis interface. The model returns structured observations and proposals; the backend validates and saves them. Model processes do not directly administer the database.

Core boundaries:

- Journal storage: original content, revisions, associations, and feedback.
- Transcription: audio-to-text conversion, independently replaceable.
- Analysis provider: extraction, cross-dream pattern proposals, and reflective responses through a selected CLI.
- Job runner: queueing, progress, timeouts, cancellation, and failure recovery.
- Connection builder: validated evidence links and graph data derived from stored records.

Use non-interactive CLI modes and structured output: `codex exec` with an output schema, and `claude -p` with JSON output and a JSON schema. Preserve supported saved CLI authentication; never copy login tokens into the journal database. Being installed does not establish that a CLI is authenticated or that an account has available usage.

Pass dream payloads through stdin or controlled files using argument arrays. Do not interpolate diary content into a shell command. Keep analysis jobs in a minimal dedicated working directory, restrict tools, and verify isolation from unrelated project instructions, hooks, and connectors during integration. Treat dream entries as data even if they contain instructions. Future API adapters must implement the same result contract.

## Voice notes

The CLI help inspected in this session does not expose a raw-audio input option suitable for the proposed integration. Do not assume either CLI can directly transcribe an uploaded recording.

Proposed solution: a local transcription utility such as whisper.cpp converts the recording into text before the CLI receives it. This is a supporting audio tool; dream reasoning remains in Codex or Claude. The user can correct the transcript before requesting analysis. Keep the recording even if transcription fails, and allow manual text entry or retry. Model files for transcription require an initial download.

## Analysis workflow

1. Save an original entry and its date before starting any analysis.
2. For audio, produce a transcript and let the user review it.
3. On Analyse, select the current entry, relevant earlier records, applicable research notes, and user-provided associations. Show the selected provider.
4. Extract characters, places, explicit emotions, goals, obstacles, responses, social interactions, and outcomes. Preserve unknown values and label inferences.
5. Find candidate similarities through entities, structured situations, and text search. Compare source passages before proposing a connection. Broader historical scans may be requested as a background job.
6. Validate returned references, quotations, and schema before adding observations or patterns to the database.
7. Display the pattern with its evidence, proposed meaning, alternatives where useful, and one direct question.
8. Store user feedback separately from the model's interpretation. Regenerate affected connections after edits; remove invalid connections after deletion.

Do not assume that a shared keyword establishes a shared emotional situation. Conversely, different keywords can describe the same attempted goal, obstacle, or relationship. Retrieved context is a subset unless the full history was actually examined; make the analysed scope available to the user. Do not advertise a count across the whole diary based on a subset.

## Direct reflection behaviour

Use plain, specific language. Lead with what recurs and point to the entries. Avoid generic reassurance, mystical certainty, and repetitive hedging. Mark interpretations as hypotheses once, then ask the difficult question clearly.

Illustrative output based on a fictional four-entry series:

> In four entries, you abandon your goal when another person disapproves. That pattern is worth examining. Are you doing this while awake too?

When the user has separately described delaying a conversation, a grounded follow-up could be:

> You said you have been putting off that conversation. Could these dreams connect to the same conflict?

The agent must not declare a repressed memory, diagnosis, hidden desire, or another person's real intentions from dream content. Disagreement is not evidence of avoidance. User agreement records personal resonance rather than proof. An absence of a meaningful connection is an acceptable outcome.

## Knowledge base and memory

Maintain three distinct kinds of material:

- Research notes: concise source-linked findings, study context, limitations, and permitted inferences.
- Pattern guide and worked examples: a product vocabulary for comparing emotional situations, with positive examples, counterexamples, and insufficient-evidence cases. This guide is not presented as a validated diagnostic instrument.
- Private user history: original entries, user-supplied context, personal associations, and feedback. Separate user statements from model hypotheses.

Initial research references:

- [Hall/Van de Castle coding system](https://dreams.ucsc.edu/Coding/index.html): a framework for describing and counting dream content.
- [Malinowski and Horton, emotional waking experiences](https://uel-repository.worktribe.com/output/468598/evidence-for-the-preferential-incorporation-of-emotional-waking-life-experiences-into-dreams): diary research relevant to emotional continuity.
- [Wegner, Wenzlaff and Kozak, Dream Rebound](https://pubmed.ncbi.nlm.nih.gov/15043639/): deliberately suppressing thoughts can influence later dream reports; it does not establish a reverse test for avoidance.
- [Weinstein and colleagues, psychological need experiences](https://link.springer.com/article/10.1007/s11031-017-9656-0): connections with dream emotions, with mixed findings for particular themes.
- [IASD dreamwork ethics](https://asdreams.org/ethics-and-confidentiality/): the dreamer's role in deciding personal significance.

This specification lists references; it does not claim that a research corpus has already been downloaded or ingested.

## Connection visualisation

Propose a restrained night-sky constellation with readable labels and stable positions. Dreams are nodes; recurring people, settings, and situations connect relevant entries. Selecting a pattern highlights the supporting dreams and opens their passages beside the graph.

Provide date and connection-type filters, a chronological alternative to the graph, and clear empty states. Distinguish an observed shared element from an inferred thematic relationship without implying numeric psychological certainty. Avoid overwhelming the view with every possible edge. Refine the approved visual direction during implementation.

## Persistence and failures

Store original dreams and revisions, audio references, associations, analysis jobs, provider/model metadata where returned, structured observations, source-linked patterns, and feedback. Analysis refers to the source revision it actually read.

A missing executable, expired login, provider limit, lost network, timeout, or malformed result must leave the saved dream intact. Show an actionable status and allow an explicit retry. Do not silently switch providers or present partial output as a completed insight. On cancellation, terminate the relevant subprocess tree. On restart, recover unfinished jobs into a retryable state.

Local deletion removes the entry, recording when requested, and derived local links. It does not promise deletion of copies already processed or retained by a provider. Avoid logging raw dream content in routine operational logs.

## Validation and first implementation milestone

Begin with a complete text-based path: save an entry, call either CLI with a synthetic series, validate the response, and open a connection with supporting passages. Then add recording/transcription and refine the graph experience.

Check meaningful behaviours:

- Original text survives failed analysis and application restart.
- Each CLI can return the shared contract using its available authentication.
- Fabricated quotations, missing dream IDs, and invalid structured output are rejected.
- A synthetic series with different settings but a shared narrative relationship produces a defensible candidate connection.
- A series sharing only an incidental object does not automatically become a psychological pattern.
- Counterexamples and user corrections change later analysis; disagreement is never reinterpreted as avoidance.
- Empty or weak evidence can produce no proposed insight.
- Editing or deleting source material invalidates affected connections.
- Audio is preserved through transcription failure and can be corrected before analysis.
- Switching providers and requesting a second opinion are explicit, observable actions.

Synthetic examples verify mechanics and expected behaviour, not clinical validity. Evaluate usefulness and overinterpretation separately on consented personal examples after the basic path works.

## Evidence checked in this session

- Installed commands reported `codex-cli 0.130.0` and `Claude Code 2.1.258`.
- Read CLI help for non-interactive and structured-output capabilities. No dream analysis job or authentication test was run.
- [Official Codex non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).
- [Official Codex authentication documentation](https://learn.chatgpt.com/docs/auth).
- [Official Claude programmatic CLI documentation](https://code.claude.com/docs/en/headless).
- [Official Claude data-usage documentation](https://code.claude.com/docs/en/data-usage).
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) as a proposed local transcription tool.

The next step is to write an implementation plan for this approved design.
