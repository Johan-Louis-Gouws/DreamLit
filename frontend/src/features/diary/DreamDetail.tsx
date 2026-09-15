import { useModal } from "../../useModal";
import { useEffect, useState } from "react";
import {
  X,
  Feather,
  Sparkles,
  ArrowUpRight,
  Trash2,
  History,
} from "lucide-react";
import { api, json, dateLabel } from "../../api";
import type { Dream, Analysis, Job, Provider } from "../../types";
import { ContextSources } from "../insights/shared";
import { JobProgress } from "../../JobProgress";

export function DreamDetail({
  id,
  provider,
  onClose,
  onChange,
  onPattern,
}: {
  id: string;
  provider: Provider;
  onClose: () => void;
  onChange: () => void;
  onPattern: (id: string) => void;
}) {
  const modalRef = useModal(onClose);
  const [dream, setDream] = useState<Dream | null>(null),
    [analyses, setAnalyses] = useState<Analysis[]>([]),
    [text, setText] = useState(""),
    [context, setContext] = useState(""),
    [edit, setEdit] = useState(false),
    [original, setOriginal] = useState<Dream | null>(null),
    [job, setJob] = useState<Job | null>(null),
    [error, setError] = useState(""),
    [transcript, setTranscript] = useState<{ id: string; text: string } | null>(
      null,
    ),
    [deleting, setDeleting] = useState(false),
    [deleteAudio, setDeleteAudio] = useState(true);
  const load = async () => {
    const d = await api<Dream>(`/dreams/${id}`);
    setDream(d);
    setText(d.text);
    setContext(d.context);
    setAnalyses(await api<Analysis[]>(`/dreams/${id}/analyses`));
    const activity = await api<{
      job: Job | null;
      transcript: { id: string; text: string } | null;
    }>(`/dreams/${id}/activity`);
    setJob(activity.job);
    setTranscript(activity.transcript);
  };
  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [id]);
  async function done(next: Job) {
    if (next.state === "completed") {
      setAnalyses(await api<Analysis[]>(`/dreams/${id}/analyses`));
      onChange();
      if (next.kind === "transcription" && next.result_id)
        setTranscript(await api(`/transcripts/${next.result_id}`));
    }
  }
  async function analyse() {
    try {
      setError("");
      setJob(
        await api<Job>(`/dreams/${id}/analyse`, json("POST", { provider })),
      );
    } catch (e) {
      setError(String(e));
    }
  }
  async function save() {
    if (!dream) return;
    try {
      setDream(
        await api<Dream>(
          `/dreams/${id}`,
          json("PUT", {
            dreamed_on: dream.dreamed_on,
            text,
            context,
            expected_revision: dream.revision,
          }),
        ),
      );
      setEdit(false);
      await load();
      onChange();
    } catch (e) {
      setError(String(e));
    }
  }
  const latest =
    analyses.find((a) => !a.stale && a.patterns.length) ||
    analyses.find((a) => !a.stale);
  return (
    <div
      className="overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <aside
        ref={modalRef}
        className="detail-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Dream entry"
      >
        <div className="panel-top">
          <span className="eyebrow">FROM YOUR DIARY</span>
          <button
            className="icon-button"
            aria-label="Close dream"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        {dream && (
          <>
            <div className="entry-date">
              {dateLabel(dream.dreamed_on)} · ENTRY{" "}
              {dream.id.slice(0, 6).toUpperCase()}
            </div>
            <h2>
              {dream.text
                ? dream.text.split(/[.!?\n]/)[0].slice(0, 85)
                : "A voice from the night"}
            </h2>
            {dream.audio_id && (
              <div className="audio-block">
                <audio controls src={`/api/audio/${dream.audio_id}`} />
                <button
                  className="text-button"
                  onClick={async () => {
                    try {
                      setJob(
                        await api<Job>(`/dreams/${id}/transcribe`, {
                          method: "POST",
                        }),
                      );
                    } catch (e) {
                      setError(String(e));
                    }
                  }}
                >
                  Transcribe locally <ArrowUpRight size={14} />
                </button>
              </div>
            )}
            {edit ? (
              <div className="edit-fields">
                <label>
                  Dream
                  <textarea
                    aria-label="Edit dream"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                  />
                </label>
                <label>
                  Waking-life context
                  <textarea
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                  />
                </label>
                <div className="button-row">
                  <button className="primary" onClick={save}>
                    Save changes
                  </button>
                  <button
                    className="text-button"
                    onClick={() => setEdit(false)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="dream-prose">
                  {dream.text ||
                    "Transcribe this recording, or write what you remember."}
                </p>
                {dream.context && (
                  <div className="context-note">
                    <span className="eyebrow">WAKING-LIFE CONTEXT</span>
                    <p>{dream.context}</p>
                  </div>
                )}
                <div className="button-row">
                  <button className="text-button" onClick={() => setEdit(true)}>
                    <Feather size={14} /> Edit entry
                  </button>
                  {dream.revision > 1 && (
                    <button
                      className="text-button"
                      onClick={async () =>
                        setOriginal(
                          await api<Dream>(`/dreams/${id}/revisions/1`),
                        )
                      }
                    >
                      <History size={14} /> Original
                    </button>
                  )}
                </div>
              </>
            )}
            {original && (
              <div className="context-note">
                <button
                  className="icon-button float-right"
                  aria-label="Close original"
                  onClick={() => setOriginal(null)}
                >
                  <X size={14} />
                </button>
                <span className="eyebrow">ORIGINAL ENTRY</span>
                <p>{original.text || "Original voice recording"}</p>
              </div>
            )}
            {transcript && (
              <div className="context-note">
                <span className="eyebrow">REVIEW TRANSCRIPT</span>
                <textarea
                  aria-label="Review transcript"
                  value={transcript.text}
                  onChange={(e) =>
                    setTranscript({ ...transcript, text: e.target.value })
                  }
                />
                <button
                  className="primary"
                  onClick={async () => {
                    try {
                      await api(
                        `/dreams/${id}/accept-transcript`,
                        json("POST", {
                          transcript_id: transcript.id,
                          text: transcript.text,
                        }),
                      );
                      setTranscript(null);
                      await load();
                      onChange();
                    } catch (e) {
                      setError(String(e));
                    }
                  }}
                >
                  Use this transcript
                </button>
              </div>
            )}
            <div className="analysis-heading">
              <h3>Follow the thread</h3>
              <span className="provider-tag">
                {provider === "codex" ? "Codex" : "Claude"} CLI
              </span>
            </div>
            <p className="muted small">
              Explore recurring people, places, and the situations underneath
              the story.
            </p>
            <button
              className="primary full"
              disabled={
                !dream.text.trim() ||
                job?.state === "running" ||
                job?.state === "queued"
              }
              onClick={analyse}
            >
              <Sparkles size={16} /> Analyse dream
            </button>
            {job && (
              <JobProgress
                onUpdate={setJob}
                key={job.id}
                initial={job}
                provider={provider}
                onDone={(next) => {
                  done(next).catch((e) => setError(String(e)));
                }}
              />
            )}
            {latest && (
              <div className="analysis-result">
                <div className="eyebrow">
                  {latest.provider.toUpperCase()} ·{" "}
                  {latest.scope.included_dream_ids.length} DREAMS CONSIDERED
                  {latest.scope.truncated ? " · SELECTED HISTORY" : ""}
                </div>
                <p>{latest.output.summary}</p>
                <ContextSources sources={latest.personal_context_sources} />
                <div className="tags">
                  {latest.output.observations.slice(0, 8).map((o, i) => (
                    <span key={i}>
                      {o.label}
                      {o.inferred ? " ?" : ""}
                    </span>
                  ))}
                </div>
                {latest.patterns.map((p) => (
                  <button
                    className="pattern-link"
                    key={p.id}
                    onClick={() => onPattern(p.id)}
                  >
                    <span>{p.title}</span>
                    <ArrowUpRight size={17} />
                  </button>
                ))}
                {!latest.patterns.length && (
                  <p className="muted small">
                    No recurring connection was established in this analysis.
                  </p>
                )}
              </div>
            )}
            {analyses.some((a) => a.stale) && (
              <p className="muted small">
                Earlier analysis refers to an older version. Re-analyse to
                refresh connections.
              </p>
            )}
            <div className="delete-section">
              {deleting ? (
                <>
                  <p>Delete this dream and its derived connections?</p>
                  {dream.audio_id && (
                    <label className="checkbox">
                      <input
                        type="checkbox"
                        checked={deleteAudio}
                        onChange={(e) => setDeleteAudio(e.target.checked)}
                      />{" "}
                      Delete the recording too
                    </label>
                  )}
                  <div className="button-row">
                    <button
                      className="danger"
                      onClick={async () => {
                        try {
                          await api(
                            `/dreams/${id}?delete_audio=${deleteAudio}`,
                            { method: "DELETE" },
                          );
                          onChange();
                          onClose();
                        } catch (e) {
                          setError(String(e));
                        }
                      }}
                    >
                      Delete dream
                    </button>
                    <button
                      className="text-button"
                      onClick={() => setDeleting(false)}
                    >
                      Keep it
                    </button>
                  </div>
                </>
              ) : (
                <button
                  className="text-button muted"
                  onClick={() => setDeleting(true)}
                >
                  <Trash2 size={14} /> Delete entry
                </button>
              )}
            </div>
          </>
        )}
        {error && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
      </aside>
    </div>
  );
}
