import { useEffect, useState } from "react";
import { Archive, Compass, Edit3, Plus, RotateCcw } from "lucide-react";
import { api, json } from "../../api";
import type { Dream, InsightRun, Provider } from "../../types";
import type { InvestigationData, InvestigationRecord } from "./types";
import {
  ConfirmDelete,
  EmptyState,
  GenerateInsight,
  InsightResult,
  StatusPill,
  Tabs,
  ViewHeader,
} from "./shared";

const blank: InvestigationData = {
  question: "",
  notes: "",
  conclusion: "",
  status: "open",
  dream_ids: [],
};

export function Explore({
  provider,
  dreams,
  onDream,
}: {
  provider: Provider;
  dreams: Dream[];
  onDream: (id: string) => void;
}) {
  const [tab, setTab] = useState("turning");
  const [investigations, setInvestigations] = useState<InvestigationRecord[]>(
    [],
  );
  const [turningRuns, setTurningRuns] = useState<InsightRun[]>([]);
  const [investigationRuns, setInvestigationRuns] = useState<InsightRun[]>([]);
  const [editing, setEditing] = useState<InvestigationRecord | null | "new">(
    null,
  );
  const [data, setData] = useState<InvestigationData>(blank);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const load = async () => {
    const [records, turns, inquiries] = await Promise.all([
      api<InvestigationRecord[]>("/insights/records?kind=investigation"),
      api<InsightRun[]>("/insights/runs?kind=turning_points"),
      api<InsightRun[]>("/insights/runs?kind=investigation"),
    ]);
    setInvestigations(records);
    setTurningRuns(turns);
    setInvestigationRuns(inquiries);
    setLoading(false);
  };
  useEffect(() => {
    load().catch((e) => {
      setError(String(e));
      setLoading(false);
    });
  }, []);
  function openForm(record?: InvestigationRecord) {
    setEditing(record || "new");
    setData(
      record
        ? { ...record.data, dream_ids: [...record.data.dream_ids] }
        : blank,
    );
    setError("");
  }
  async function save() {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      if (editing && editing !== "new")
        await api(
          `/insights/records/${editing.id}`,
          json("PUT", { expected_revision: editing.revision, data }),
        );
      else
        await api(
          "/insights/records",
          json("POST", { kind: "investigation", data }),
        );
      setEditing(null);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }
  async function setStatus(
    record: InvestigationRecord,
    status: InvestigationData["status"],
  ) {
    try {
      await api(
        `/insights/records/${record.id}`,
        json("PUT", {
          expected_revision: record.revision,
          data: { ...record.data, status },
        }),
      );
      await load();
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <div className="insights-page">
      <ViewHeader
        eyebrow="FOLLOW WHAT CHANGES"
        title={
          <>
            Explore the <em>turning points</em>
          </>
        }
      >
        Compare how situations unfold, or keep a question open long enough to
        find both examples and exceptions.
      </ViewHeader>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "turning", label: "Turning Points" },
          { id: "investigations", label: "Investigations" },
        ]}
      />
      {tab === "turning" ? (
        <section className="feature-section turning-points">
          <div className="section-lead">
            <div>
              <span className="eyebrow">EARLIER / LATER</span>
              <h2>Notice a different response.</h2>
              <p>
                DreamLit compares dated situations and cites both passages.
                Sometimes the honest result is that nothing changed.
              </p>
            </div>
            <GenerateInsight
              kind="turning_points"
              provider={provider}
              label={
                turningRuns[0]?.stale
                  ? "Compare again"
                  : "Compare turning points"
              }
              onCreated={(run) => setTurningRuns((items) => [run, ...items])}
            />
          </div>
          {!loading && !turningRuns.length && (
            <EmptyState icon={<Compass />} title="No comparison yet">
              Two or more dated dreams give this reflection somewhere to begin.
            </EmptyState>
          )}
          {turningRuns.map((run) => (
            <div key={run.id}>
              <InsightResult run={run} onDream={onDream} />
              <button
                className="secondary"
                onClick={() => {
                  openForm();
                  setData({
                    ...blank,
                    question: run.output.question,
                    dream_ids: run.scope.included_dream_ids,
                  });
                  setTab("investigations");
                }}
              >
                Investigate this turning point
              </button>
            </div>
          ))}
          {error && (
            <p role="alert" className="error-message">
              {error}
            </p>
          )}
        </section>
      ) : (
        <section className="feature-section investigations">
          <div className="section-lead">
            <div>
              <span className="eyebrow">A QUESTION WITH A LONGER LIFE</span>
              <h2>Investigate this.</h2>
              <p>
                Save a question and gather support, counterexamples,
                alternatives, and an open edge. Resolve it when your own
                conclusion feels ready.
              </p>
            </div>
            <button className="secondary" onClick={() => openForm()}>
              <Plus size={15} /> Start an investigation
            </button>
          </div>
          {editing && (
            <div className="record-form paper-form">
              <div className="card-top">
                <span className="eyebrow">
                  {editing === "new"
                    ? "NEW INVESTIGATION"
                    : "REVISE INVESTIGATION"}
                </span>
                <button
                  className="text-button"
                  onClick={() => setEditing(null)}
                >
                  Cancel
                </button>
              </div>
              <label>
                Investigation question
                <input
                  value={data.question}
                  onChange={(e) =>
                    setData({ ...data, question: e.target.value })
                  }
                />
              </label>
              <label>
                Investigation notes
                <textarea
                  value={data.notes}
                  onChange={(e) => setData({ ...data, notes: e.target.value })}
                />
              </label>
              <label>
                Conclusion
                <textarea
                  value={data.conclusion}
                  onChange={(e) =>
                    setData({ ...data, conclusion: e.target.value })
                  }
                  placeholder="Leave open until something becomes clear"
                />
              </label>
              <div className="form-grid compact">
                <label>
                  Investigation status
                  <select
                    value={data.status}
                    onChange={(e) =>
                      setData({
                        ...data,
                        status: e.target.value as InvestigationData["status"],
                      })
                    }
                  >
                    <option value="open">Open</option>
                    <option value="resolved">Resolved</option>
                    <option value="archived">Archived</option>
                  </select>
                </label>
              </div>
              {!!dreams.length && (
                <fieldset className="dream-picker">
                  <legend>Linked dreams (optional)</legend>
                  {dreams.map((dream) => (
                    <label key={dream.id}>
                      <input
                        type="checkbox"
                        checked={data.dream_ids.includes(dream.id)}
                        onChange={(e) =>
                          setData({
                            ...data,
                            dream_ids: e.target.checked
                              ? [...data.dream_ids, dream.id]
                              : data.dream_ids.filter((id) => id !== dream.id),
                          })
                        }
                      />
                      <span>{dream.dreamed_on}</span>
                      {dream.text.slice(0, 75)}
                    </label>
                  ))}
                </fieldset>
              )}
              <button
                className="primary"
                disabled={saving || !data.question.trim()}
                onClick={save}
              >
                {editing === "new" ? "Save investigation" : "Save changes"}
              </button>
              {error && (
                <p role="alert" className="error-message">
                  {error}
                </p>
              )}
            </div>
          )}
          {loading && (
            <p className="loading-line">
              <span className="status-dot" /> Opening investigations…
            </p>
          )}
          {!loading && !investigations.length && !editing && (
            <EmptyState title="No open questions yet">
              Begin with something you want to understand without rushing toward
              certainty.
            </EmptyState>
          )}
          <div className="record-stack">
            {investigations.map((record) => {
              const run = investigationRuns.find(
                (item) => item.subject_id === record.id,
              );
              return (
                <article
                  className={`record-card investigation-card ${record.data.status}`}
                  aria-label={`Investigation: ${record.data.question}`}
                  key={record.id}
                >
                  <div className="card-top">
                    <div>
                      <span className="record-kicker">
                        INVESTIGATION · REVISION {record.revision}
                      </span>
                      <h3>{record.data.question}</h3>
                    </div>
                    <StatusPill tone={record.data.status}>
                      {record.data.status[0].toUpperCase() +
                        record.data.status.slice(1)}
                    </StatusPill>
                  </div>
                  {record.data.notes && <p>{record.data.notes}</p>}
                  {!!record.data.dream_ids.length && (
                    <div className="record-links">
                      <span>
                        {record.data.dream_ids.length} linked dream
                        {record.data.dream_ids.length === 1 ? "" : "s"}
                      </span>
                    </div>
                  )}
                  {record.data.conclusion && (
                    <div className="conclusion">
                      <span className="eyebrow">YOUR CONCLUSION</span>
                      <p>{record.data.conclusion}</p>
                    </div>
                  )}
                  <div className="card-actions">
                    {record.data.status !== "archived" && (
                      <GenerateInsight
                        kind="investigation"
                        subjectId={record.id}
                        provider={provider}
                        label={
                          run?.stale ? "Investigate again" : "Investigate this"
                        }
                        onCreated={(next) =>
                          setInvestigationRuns((items) => [next, ...items])
                        }
                      />
                    )}
                    <button
                      className="text-button"
                      onClick={() => openForm(record)}
                    >
                      <Edit3 size={13} /> Edit investigation
                    </button>
                    {record.data.status === "open" ? (
                      <button
                        className="text-button"
                        onClick={() => setStatus(record, "archived")}
                      >
                        <Archive size={13} /> Archive
                      </button>
                    ) : (
                      <button
                        className="text-button"
                        onClick={() => setStatus(record, "open")}
                      >
                        <RotateCcw size={13} /> Reopen investigation
                      </button>
                    )}
                    <ConfirmDelete
                      label="investigation"
                      onDelete={async () => {
                        await api(`/insights/records/${record.id}`, {
                          method: "DELETE",
                        });
                        await load();
                      }}
                    />
                  </div>
                  {run && <InsightResult run={run} onDream={onDream} />}
                </article>
              );
            })}
          </div>
          {error && !editing && (
            <p role="alert" className="error-message">
              {error}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
