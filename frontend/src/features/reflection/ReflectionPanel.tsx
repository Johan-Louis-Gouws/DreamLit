import { useModal } from "../../useModal";
import { useEffect, useState } from "react";
import { X, ArrowUpRight, Send } from "lucide-react";
import { api, json } from "../../api";
import type { Pattern, Job, Provider } from "../../types";
import { JobProgress } from "../../JobProgress";

export function ReflectionPanel({
  id,
  provider,
  onClose,
  onDream,
}: {
  id: string;
  provider: Provider;
  onClose: () => void;
  onDream: (id: string) => void;
}) {
  const modalRef = useModal(onClose);
  const [pattern, setPattern] = useState<Pattern | null>(null),
    [message, setMessage] = useState(""),
    [note, setNote] = useState(""),
    [job, setJob] = useState<Job | null>(null),
    [error, setError] = useState(""),
    [feedback, setFeedback] = useState("");
  const load = () => api<Pattern>(`/patterns/${id}`).then(setPattern);
  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [id]);
  async function reply() {
    if (!message.trim()) return;
    try {
      setJob(
        await api<Job>(
          `/patterns/${id}/reflect`,
          json("POST", { provider, message }),
        ),
      );
      setMessage("");
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <div
      className="overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <aside
        ref={modalRef}
        className="detail-panel reflection-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Pattern reflection"
      >
        <div className="panel-top">
          <span className="eyebrow">A THREAD WORTH FOLLOWING</span>
          <button
            className="icon-button"
            aria-label="Close reflection"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        {pattern && (
          <>
            <h2>{pattern.title}</h2>
            <span className="provider-tag">{pattern.provider} CLI</span>
            {pattern.stale && (
              <p className="error-message">
                A source has changed. Re-analyse the dream to refresh this
                pattern.
              </p>
            )}
            <p className="pattern-observation">{pattern.observation}</p>
            {pattern.hypothesis && (
              <div className="hypothesis">
                <div className="eyebrow">POSSIBLE EXPLANATION</div>
                <p>{pattern.hypothesis}</p>
              </div>
            )}
            <div className="direct-question">{pattern.question}</div>
            <section
              className="evidence-section"
              role="region"
              aria-label="Supporting dreams"
            >
              <div className="eyebrow">IN YOUR OWN WORDS</div>
              {pattern.evidence.map((ref, i) => (
                <div className="evidence-quote" key={i}>
                  <blockquote>{ref.quote}</blockquote>
                  <button onClick={() => onDream(ref.dream_id)}>
                    Open{" "}
                    {ref.field === "context" ? "waking-life note" : "dream"} ·
                    revision {ref.revision}
                    <ArrowUpRight size={13} />
                  </button>
                </div>
              ))}
            </section>
            {!!pattern.counterevidence?.length && (
              <section
                className="evidence-section"
                aria-label="Counterexamples"
              >
                <div className="eyebrow">WHERE IT DIFFERS</div>
                <p className="small muted">
                  These passages challenge or narrow the pattern.
                </p>
                {pattern.counterevidence.map((ref, i) => (
                  <div className="evidence-quote" key={i}>
                    <blockquote>{ref.quote}</blockquote>
                    <button onClick={() => onDream(ref.dream_id)}>
                      Open dream · revision {ref.revision}{" "}
                      <ArrowUpRight size={13} />
                    </button>
                  </div>
                ))}
              </section>
            )}
            {pattern.alternatives.length > 0 && (
              <details className="alternatives">
                <summary>Other ways to read this</summary>
                {pattern.alternatives.map((a, i) => (
                  <p key={i}>{a}</p>
                ))}
              </details>
            )}
            <div className="feedback-box">
              <label htmlFor="feedback-note" className="eyebrow">
                DOES THIS FIT YOUR EXPERIENCE?
              </label>
              <textarea
                id="feedback-note"
                placeholder="Add your perspective (optional)"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <div className="feedback-buttons">
                {[
                  ["resonates", "Resonates"],
                  ["does_not_fit", "Does not fit"],
                  ["unsure", "Unsure"],
                ].map(([value, label]) => (
                  <button
                    className={feedback === value ? "selected" : ""}
                    key={value}
                    onClick={async () => {
                      try {
                        await api(
                          `/patterns/${id}/feedback`,
                          json("POST", { verdict: value, note }),
                        );
                        setFeedback(value);
                        await load();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {feedback && (
                <small role="status">
                  Your perspective is saved for future reflections.
                </small>
              )}
            </div>
            <div className="conversation">
              {pattern.reflections?.map((turn) => (
                <div key={turn.id}>
                  <div className="user-turn">{turn.message}</div>
                  <div className="assistant-turn">
                    <span className="eyebrow">{turn.provider} REFLECTION</span>
                    <p>{turn.output.response}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="reply-box">
              <textarea
                aria-label="Continue the reflection"
                placeholder="Be honest. What comes to mind?"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
              <button
                className="icon-button"
                aria-label="Send reflection"
                disabled={
                  !message.trim() ||
                  job?.state === "running" ||
                  job?.state === "queued" ||
                  !!pattern.stale
                }
                onClick={reply}
              >
                <Send size={18} />
              </button>
            </div>
            {job && (
              <JobProgress
                onUpdate={setJob}
                key={job.id}
                initial={job}
                provider={provider}
                onDone={() => {
                  load().catch((e) => setError(String(e)));
                }}
              />
            )}
            <button
              className="text-button second-opinion"
              disabled={
                !!pattern.stale ||
                job?.state === "running" ||
                job?.state === "queued"
              }
              onClick={async () => {
                try {
                  const other =
                    pattern.provider === "codex" ? "claude" : "codex";
                  setJob(
                    await api<Job>(
                      `/patterns/${id}/second-opinion`,
                      json("POST", { provider: other }),
                    ),
                  );
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              Ask {pattern.provider === "codex" ? "Claude" : "Codex"} for a
              second opinion <ArrowUpRight size={15} />
            </button>
            <p className="small muted">
              A second opinion sends the supporting context to that provider.
            </p>
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
