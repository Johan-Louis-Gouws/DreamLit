import { useEffect, useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  BookOpen,
  LoaderCircle,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";
import { api, dateLabel, json } from "../../api";
import { JobProgress } from "../../JobProgress";
import type {
  InsightEvidence,
  InsightRecord,
  InsightRun,
  InsightSource,
  Job,
  Provider,
  PersonalContextSource,
  RunKind,
} from "../../types";

export function ViewHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  children: ReactNode;
}) {
  return (
    <header className="insight-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{children}</p>
      </div>
      <div className="insight-orbit" aria-hidden="true">
        <span>✦</span>
        <i />
        <i />
        <i />
      </div>
    </header>
  );
}

export function Tabs({
  value,
  onChange,
  items,
}: {
  value: string;
  onChange: (value: string) => void;
  items: { id: string; label: string }[];
}) {
  return (
    <div className="insight-tabs" role="tablist">
      {items.map((item, index) => (
        <button
          key={item.id}
          role="tab"
          aria-selected={value === item.id}
          tabIndex={value === item.id ? 0 : -1}
          onKeyDown={(event) => {
            const offset =
              event.key === "ArrowRight"
                ? 1
                : event.key === "ArrowLeft"
                  ? -1
                  : 0;
            if (!offset) return;
            event.preventDefault();
            const next = (index + offset + items.length) % items.length;
            onChange(items[next].id);
            (
              event.currentTarget.parentElement?.children[
                next
              ] as HTMLButtonElement
            )?.focus();
          }}
          className={value === item.id ? "active" : ""}
          onClick={() => onChange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function StatusPill({
  children,
  tone = "plain",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

export function ConfirmDelete({
  label,
  onDelete,
}: {
  label: string;
  onDelete: () => Promise<void>;
}) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!confirming)
    return (
      <button
        className="text-button danger-text"
        onClick={() => setConfirming(true)}
      >
        Delete {label}
      </button>
    );
  return (
    <span className="confirm-inline">
      Delete permanently?{" "}
      <button
        className="danger"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await onDelete();
          } catch (e) {
            setError(String(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        Delete
      </button>
      <button className="text-button" onClick={() => setConfirming(false)}>
        Keep it
      </button>
      {error && <span role="alert">{error}</span>}
    </span>
  );
}

export function RecordHistory({
  record,
  onClose,
}: {
  record: InsightRecord;
  onClose: () => void;
}) {
  const [history, setHistory] = useState<InsightRecord[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<InsightRecord[]>(`/insights/records/${record.id}/history`)
      .then(setHistory)
      .catch((e) => setError(String(e)));
  }, [record.id]);
  return (
    <div className="history-drawer" role="region" aria-label="Record history">
      <div className="card-top">
        <span className="eyebrow">ORIGINAL VERSIONS</span>
        <button
          className="icon-button"
          aria-label="Close history"
          onClick={onClose}
        >
          <X size={16} />
        </button>
      </div>
      {history.length === 0 && !error && (
        <p className="small muted">
          <LoaderCircle className="spin" size={14} /> Loading history…
        </p>
      )}
      {history.map((version) => (
        <div className="history-version" key={version.revision}>
          <small>
            Revision {version.revision} ·{" "}
            {new Date(version.updated_at).toLocaleDateString()}
          </small>
          <RecordFields data={version.data} />
        </div>
      ))}
      {error && (
        <p role="alert" className="error-message">
          {error}
        </p>
      )}
    </div>
  );
}

function evidenceSource(run: InsightRun, evidence: InsightEvidence) {
  return run.sources.find(
    (source) =>
      source.kind === evidence.source_kind &&
      source.id === evidence.source_id &&
      source.revision === evidence.revision,
  );
}

function Citation({
  source,
  evidence,
  onDream,
}: {
  source?: InsightSource;
  evidence: InsightEvidence;
  onDream: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState<InsightRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const quoted = evidence.quote;
  async function reveal() {
    if (source?.kind === "dream") {
      onDream(source.id);
      return;
    }
    setOpen(!open);
    if (!open && source && !history.length) {
      setLoading(true);
      try {
        setHistory(
          await api<InsightRecord[]>(`/insights/records/${source.id}/history`),
        );
      } catch {
        setHistory([]);
      } finally {
        setLoading(false);
      }
    }
  }
  return (
    <div className="source-quote">
      <blockquote>“{quoted}”</blockquote>
      <button
        onClick={reveal}
        aria-label={
          source?.kind === "dream"
            ? `Open dream source: ${source.label}`
            : `View context source: ${source?.label || "personal context"}`
        }
      >
        {source?.kind === "dream" ? "Open dream source" : "View saved context"}{" "}
        · {source?.date || "source"} <ArrowUpRight size={13} />
      </button>
      {open && source?.kind !== "dream" && (
        <div className="source-context">
          {loading ? (
            <span>Loading original revision…</span>
          ) : (
            <>
              <strong>
                {source?.label} · revision {source?.revision}
              </strong>
              {Object.entries(source?.fields || {}).map(([field, value]) => (
                <p key={field}>
                  <span>{field.replaceAll("_", " ")}</span>
                  {value}
                </p>
              ))}
              {history.find((item) => item.revision === source?.revision) && (
                <small>Saved revision {source?.revision}.</small>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export function InsightResult({
  run,
  onDream,
}: {
  run: InsightRun;
  onDream: (id: string) => void;
}) {
  return (
    <article
      className={`generated-insight ${run.stale ? "stale" : ""}`}
      aria-label={`Generated insight: ${run.output.title}`}
    >
      <div className="generated-meta">
        <span>
          {run.provider} CLI · {run.kind.replace("_", " ")} ·{" "}
          {new Date(run.created_at).toLocaleDateString()}
        </span>
        <span>
          {run.scope.included_dream_ids.length} of{" "}
          {run.scope.total_eligible_dreams} dreams included
          {run.scope.truncated ? " · selected history" : ""}
        </span>
      </div>
      {run.stale && (
        <div className="stale-note">
          <RotateCcw size={15} /> A source changed. Generate again for a current
          reflection.
        </div>
      )}
      <h2>{run.output.title}</h2>
      <p className="insight-summary">{run.output.summary}</p>
      {run.output.sections.map((section, index) => (
        <section
          className="insight-section"
          key={`${section.heading}-${index}`}
        >
          <h3>{section.heading}</h3>
          <p>{section.body}</p>
          {section.evidence.map((item, i) => (
            <Citation
              key={`e-${i}`}
              evidence={item}
              source={evidenceSource(run, item)}
              onDream={onDream}
            />
          ))}
          {!!section.counterevidence.length && (
            <div className="counter-sources">
              <span className="eyebrow">WHAT COMPLICATES IT</span>
              {section.counterevidence.map((item, i) => (
                <Citation
                  key={`c-${i}`}
                  evidence={item}
                  source={evidenceSource(run, item)}
                  onDream={onDream}
                />
              ))}
            </div>
          )}
        </section>
      ))}
      <ContextSources
        sources={
          run.sources.filter(
            (source) => source.kind !== "dream",
          ) as PersonalContextSource[]
        }
      />
      {run.output.question && (
        <div className="closing-question">
          <span>✧</span>
          <p>{run.output.question}</p>
        </div>
      )}
    </article>
  );
}

export function GenerateInsight({
  kind,
  provider,
  subjectId,
  dateFrom,
  dateTo,
  label,
  disabled = false,
  onCreated,
}: {
  kind: RunKind;
  provider: Provider;
  subjectId?: string;
  dateFrom?: string;
  dateTo?: string;
  label: string;
  disabled?: boolean;
  onCreated: (run: InsightRun) => void;
}) {
  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  return (
    <div className="generation-action">
      <button
        className="primary"
        disabled={
          disabled ||
          submitting ||
          job?.state === "queued" ||
          job?.state === "running"
        }
        onClick={async () => {
          try {
            setError("");
            setSubmitting(true);
            setJob(
              await api<Job>(
                "/insights/runs",
                json("POST", {
                  kind,
                  provider,
                  subject_id: subjectId || null,
                  date_from: dateFrom || null,
                  date_to: dateTo || null,
                }),
              ),
            );
          } catch (e) {
            setError(String(e));
          } finally {
            setSubmitting(false);
          }
        }}
      >
        <Sparkles size={15} /> {label}
      </button>
      {job && (
        <JobProgress
          initial={job}
          provider={provider}
          onUpdate={setJob}
          onDone={async (done) => {
            if (done.state === "completed" && done.result_id) {
              try {
                onCreated(
                  await api<InsightRun>(`/insights/runs/${done.result_id}`),
                );
              } catch (e) {
                setError(String(e));
              }
            }
          }}
        />
      )}
      {error && (
        <p role="alert" className="error-message">
          {error}
        </p>
      )}
    </div>
  );
}

export function EmptyState({
  icon = <BookOpen />,
  title,
  children,
  action,
}: {
  icon?: ReactNode;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="insight-empty">
      {icon}
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </div>
  );
}

export function formatPeriod(from: string, to: string) {
  const left = dateLabel(from).replace(", " + from.slice(0, 4), "");
  return `${left} – ${dateLabel(to)}`;
}

function RecordFields({ data }: { data: Record<string, unknown> }) {
  return (
    <>
      {Object.entries(data)
        .filter(
          ([key, value]) =>
            !key.endsWith("_id") &&
            !key.endsWith("_ids") &&
            value !== null &&
            value !== "",
        )
        .map(([key, value]) => (
          <p key={key}>
            <strong>{key.replaceAll("_", " ")}: </strong>
            {Array.isArray(value) ? value.join(", ") : String(value)}
          </p>
        ))}
    </>
  );
}

export function ContextSources({
  sources = [],
}: {
  sources?: PersonalContextSource[];
}) {
  const [selected, setSelected] = useState<InsightRecord | null>(null);
  const [error, setError] = useState("");
  if (!sources.length) return null;
  return (
    <details className="context-note">
      <summary>Personal context used ({sources.length})</summary>
      {sources.map((source) => (
        <div key={`${source.kind}-${source.id}-${source.revision}`}>
          <button
            className="text-button"
            onClick={async () => {
              setError("");
              setSelected(null);
              try {
                const versions = await api<InsightRecord[]>(
                  `/insights/records/${source.id}/history`,
                );
                const version = versions.find(
                  (item) => item.revision === source.revision,
                );
                if (!version)
                  throw new Error("This saved version is no longer available.");
                setSelected(version);
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            {source.label} · revision {source.revision}
          </button>
        </div>
      ))}
      {selected && (
        <div className="source-context">
          <RecordFields data={selected.data} />
        </div>
      )}
      {error && (
        <p role="alert" className="error-message">
          {error}
        </p>
      )}
    </details>
  );
}
