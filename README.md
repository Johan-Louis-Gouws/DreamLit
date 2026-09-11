# DreamLit

A local dream journal that finds recurring people, places, and emotional situations across different nights. Capture a fragment or a voice note, then follow a suggested connection back to the exact passages that support it.

The first version runs analysis through your installed **Codex CLI or Claude CLI**. You choose the provider for each job; a second opinion is a separate, explicit request. The journal and speech transcription stay on this computer. Analysis sends the selected written content and relevant journal context to the chosen provider using its CLI account.

## Start

From this folder:

```bash
uv sync
npm --prefix frontend ci
npm --prefix frontend run build
uv run python scripts/start.py
```

Open **[DreamLit](http://127.0.0.1:8765)**. Stop it with Ctrl+C. Node 20.19+ (or 22.12+) and Python 3.12+ are required; Linux is the tested platform.

The launcher keeps your private journal in `.dreamlit/journal/`. Set `DREAMLIT_DATA_DIR` to choose another location. Directly running `uv run dreamlit` uses `~/.local/share/dreamlit` unless that variable is set. Runtime downloads and personal data are ignored by Git. Local data is not encrypted by the app.

For development with automatic frontend updates:

```bash
uv run python scripts/dev.py
```

## Connect the CLIs

Use the CLIs' normal sign-in commands outside the app. Existing authenticated installations are reused. Settings shows installation status; **Test connection** makes a small, explicit provider request and may consume account usage.

This machine's system Codex was too old for its saved `gpt-6-astra` model. An app-local Codex 0.153.4 installation was verified successfully; the system installation and global configuration were left intact. Install that local version in a fresh checkout with:

```bash
npm install --prefix .dreamlit/runtime @openai/codex@0.153.4
```

The adapter prefers this installation, then the system command. `DREAMLIT_CODEX_BINARY` can override its path. Codex uses an isolated configuration while preserving the saved model and reasoning preference; Claude uses safe mode with tools disabled. No diary text is interpolated into shell commands. Missing login, usage limits, network failures, invalid quotations, and cancellation leave the saved entry intact. Retry never silently switches providers.

[Codex non-interactive usage](https://developers.openai.com/codex/noninteractive), [Claude CLI documentation](https://code.claude.com/docs/en/headless).

## Voice notes

Record or import audio, save the recording, choose **Transcribe locally**, then correct and accept the transcript. The original recording remains available. Transcription never automatically starts analysis.

FFmpeg and a C/C++ compiler must be installed. The optional setup builds [whisper.cpp](https://github.com/ggml-org/whisper.cpp) v1.8.3 with CPU inference and downloads the English `base.en` model (about 148 MB):

```bash
DREAMLIT_DATA_DIR="$PWD/.dreamlit/journal" uv run python scripts/setup_voice.py
```

The tool, model, and installation record live under `.dreamlit/voice/`. Settings allows different local executable and model paths. The included model is intended for English. Recording requires browser microphone permission; importing audio works without microphone access. Uploads are limited to 50 MB.

## Using the journal

- **Capture:** save what you remember; add waking-life context separately.
- **Diary:** search, reopen, or edit entries. Original versions are retained.
- **Analyse dream:** extract descriptions, then compare with relevant saved dreams. Each recurring theme needs quotations from at least two distinct entries.
- **Connections:** explore the constellation or timeline, filter by dates and type, or explicitly scan history for older connections.
- **Reflection:** read the observation, possible explanation, direct question, and alternatives. Mark a suggestion as resonating, uncertain, or not fitting. Your correction is supplied to later analysis with the interpretation it concerns.
- **Settings:** choose a provider, add or edit personal meanings, configure local speech, or export a ZIP including original recordings if selected.

Editing a source removes its older connections from the current graph. Re-analysis is explicit. Deleting a dream removes dependent local analyses and feedback; deletion does not remove copies previously handled by a provider. You can retain the recording when deleting an entry; retained audio is included in an export with recordings enabled.

## Knowledge and interpretation

`knowledge/research.json` contains five concise source-linked research notes, with limitations and permitted inferences. `knowledge/pattern-guide.md` describes how to compare emotional situations. `knowledge/examples.json` holds worked synthetic examples. Personal associations and feedback are stored separately in the journal.

The app is direct about what repeats and tentative about why. A shared object or generic mood is insufficient for a psychological theme. It can return no pattern. Quotations are checked against exact source IDs, fields, and revisions; this establishes provenance, not the truth of an interpretation. The model is instructed not to diagnose, infer forgotten events, or treat disagreement as avoidance.

Single-entry analysis selects complete records within a 60,000-character source budget and displays whether history was selected. History scans build a compact index and verify candidate groups against original passages. An oversized index asks for a narrower date range; oversized groups are reported as skipped. This prototype has no hosted account service, API-key integration, import/restore workflow, or mobile background recorder.

## Verification

```bash
uv run pytest
uv run ruff check backend tests scripts
npm --prefix frontend run build
npm --prefix frontend exec playwright install chromium
npm --prefix frontend run test:e2e
```

Browser tests start an isolated temporary journal on port 8766 and use a deterministic provider fixture. They never call your model accounts or seed the personal journal. The optional speech integration test uses whisper.cpp's public sample and the installed local model; it skips when voice setup is absent.

Live CLI checks and synthetic semantic evaluation are explicit, separate commands that consume account usage:

```bash
uv run python scripts/check_cli.py --provider codex
uv run python scripts/check_cli.py --provider claude
uv run python scripts/evaluate_series.py --provider both
```

Evaluation output is stored under `.dreamlit/evaluations/`. It uses invented dreams only. See [validation notes](docs/validation.md) for observed results and limitations.
