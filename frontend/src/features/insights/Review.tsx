import { useEffect, useMemo, useState } from "react";
import { Check, Edit3, FlaskConical, Mail, Plus, X } from "lucide-react";
import { api, json, today } from "../../api";
import type { InsightRun, Provider } from "../../types";
import type {
  ExperimentData,
  ExperimentRecord,
  InvestigationRecord,
  PersonRecord,
} from "./types";
import {
  ConfirmDelete,
  EmptyState,
  GenerateInsight,
  InsightResult,
  StatusPill,
  Tabs,
  ViewHeader,
  formatPeriod,
} from "./shared";

const blank: ExperimentData = {
  action: "",
  intention: "",
  outcome: "",
  due_on: null,
  status: "planned",
  investigation_id: null,
  person_id: null,
};
function weekStart(end: string) {
  if (!end) return "";
  const value = new Date(`${end}T12:00:00`);
  value.setDate(value.getDate() - 6);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

export function Review({
  provider,
  onDream,
}: {
  provider: Provider;
  onDream: (id: string) => void;
}) {
  const [tab, setTab] = useState("experiments");
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [investigations, setInvestigations] = useState<InvestigationRecord[]>(
    [],
  );
  const [people, setPeople] = useState<PersonRecord[]>([]);
  const [letters, setLetters] = useState<InsightRun[]>([]);
  const [editing, setEditing] = useState<ExperimentRecord | null | "new">(null);
  const [completing, setCompleting] = useState<ExperimentRecord | null>(null);
  const [outcome, setOutcome] = useState("");
  const [data, setData] = useState<ExperimentData>(blank);
  const [end, setEnd] = useState(today());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const start = useMemo(() => weekStart(end), [end]);
  const load = async () => {
    const [records, inquiries, savedPeople, savedLetters] = await Promise.all([
      api<ExperimentRecord[]>("/insights/records?kind=experiment"),
      api<InvestigationRecord[]>("/insights/records?kind=investigation"),
      api<PersonRecord[]>("/insights/records?kind=person"),
      api<InsightRun[]>("/insights/runs?kind=weekly"),
    ]);
    setExperiments(records);
    setInvestigations(inquiries);
    setPeople(savedPeople);
    setLetters(savedLetters);
    setLoading(false);
  };
  useEffect(() => {
    load().catch((e) => {
      setError(String(e));
      setLoading(false);
    });
  }, []);
  function openForm(record?: ExperimentRecord) {
    setEditing(record || "new");
    setData(record ? { ...record.data } : blank);
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
          json("POST", { kind: "experiment", data }),
        );
      setEditing(null);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }
  async function update(
    record: ExperimentRecord,
    next: Partial<ExperimentData>,
  ) {
    try {
      await api(
        `/insights/records/${record.id}`,
        json("PUT", {
          expected_revision: record.revision,
          data: { ...record.data, ...next },
        }),
      );
      await load();
      return true;
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <div className="insights-page">
      <ViewHeader
        eyebrow="LOOK BACK, MOVE GENTLY"
        title={
          <>
            Review what you're <em>learning</em>
          </>
        }
      >
        Choose a small action, record what happened, or gather one week into a
        modest letter with room for exceptions.
      </ViewHeader>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "experiments", label: "Experiments" },
          { id: "letter", label: "Weekly Letter" },
        ]}
      />
      {tab === "experiments" ? (
        <section className="feature-section experiments">
          <div className="section-lead">
            <div>
              <span className="eyebrow">SMALL, USER-CHOSEN ACTIONS</span>
              <h2>Try something you can notice.</h2>
              <p>
                Experiments record an intention and outcome. They do not claim
                to explain or cause what appears in later dreams.
              </p>
            </div>
            <button className="secondary" onClick={() => openForm()}>
              <Plus size={15} /> Plan an experiment
            </button>
          </div>
          {editing && (
            <div className="record-form paper-form">
              <div className="card-top">
                <span className="eyebrow">
                  {editing === "new" ? "A SMALL EXPERIMENT" : "REVISE THE PLAN"}
                </span>
                <button
                  className="text-button"
                  onClick={() => setEditing(null)}
                >
                  Cancel
                </button>
              </div>
              <label>
                Action
                <textarea
                  value={data.action}
                  onChange={(e) => setData({ ...data, action: e.target.value })}
                />
              </label>
              <label>
                Intention
                <textarea
                  value={data.intention}
                  onChange={(e) =>
                    setData({ ...data, intention: e.target.value })
                  }
                />
              </label>
              <div className="form-grid compact">
                <label>
                  Check-in date
                  <input
                    type="date"
                    value={data.due_on || ""}
                    onChange={(e) =>
                      setData({ ...data, due_on: e.target.value || null })
                    }
                  />
                </label>
                <label>
                  Status
                  <select
                    value={data.status}
                    onChange={(e) =>
                      setData({
                        ...data,
                        status: e.target.value as ExperimentData["status"],
                      })
                    }
                  >
                    <option value="planned">Planned</option>
                    <option value="active">Active</option>
                    <option value="completed">Completed</option>
                    <option value="dropped">Dropped</option>
                  </select>
                </label>
                <label>
                  Related investigation
                  <select
                    value={data.investigation_id || ""}
                    onChange={(e) =>
                      setData({
                        ...data,
                        investigation_id: e.target.value || null,
                      })
                    }
                  >
                    <option value="">None</option>
                    {investigations.map((item) => (
                      <option value={item.id} key={item.id}>
                        {item.data.question}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Related person
                  <select
                    value={data.person_id || ""}
                    onChange={(e) =>
                      setData({ ...data, person_id: e.target.value || null })
                    }
                  >
                    <option value="">None</option>
                    {people.map((item) => (
                      <option value={item.id} key={item.id}>
                        {item.data.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {editing !== "new" && (
                <label>
                  Outcome
                  <textarea
                    value={data.outcome}
                    onChange={(e) =>
                      setData({ ...data, outcome: e.target.value })
                    }
                  />
                </label>
              )}
              <button
                className="primary"
                disabled={saving || !data.action.trim()}
                onClick={save}
              >
                {editing === "new" ? "Save experiment" : "Save changes"}
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
              <span className="status-dot" /> Opening experiments…
            </p>
          )}
          {!loading && !experiments.length && !editing && (
            <EmptyState icon={<FlaskConical />} title="No experiment planned">
              Choose one action small enough to try, and an intention that
              belongs to you.
            </EmptyState>
          )}
          <div className="experiment-grid">
            {experiments.map((record) => (
              <article
                className={`record-card experiment-card ${record.data.status}`}
                aria-label={`Experiment: ${record.data.action}`}
                key={record.id}
              >
                <div className="card-top">
                  <span className="record-kicker">
                    SMALL EXPERIMENT · REVISION {record.revision}
                  </span>
                  <StatusPill tone={record.data.status}>
                    {record.data.status[0].toUpperCase() +
                      record.data.status.slice(1)}
                  </StatusPill>
                </div>
                <h3>{record.data.action}</h3>
                {record.data.intention && (
                  <p className="intention">{record.data.intention}</p>
                )}
                {record.data.due_on && (
                  <small className="due-date">
                    CHECK IN ·{" "}
                    {new Date(
                      `${record.data.due_on}T12:00:00`,
                    ).toLocaleDateString()}
                  </small>
                )}
                {record.data.outcome && (
                  <div className="conclusion">
                    <span className="eyebrow">WHAT YOU NOTICED</span>
                    <p>{record.data.outcome}</p>
                  </div>
                )}
                {completing?.id === record.id && (
                  <div className="outcome-form">
                    <label>
                      Outcome
                      <textarea
                        value={outcome}
                        onChange={(e) => setOutcome(e.target.value)}
                      />
                    </label>
                    <div className="button-row">
                      <button
                        className="primary"
                        disabled={!outcome.trim()}
                        onClick={async () => {
                          if (
                            await update(record, {
                              status: "completed",
                              outcome,
                            })
                          ) {
                            setCompleting(null);
                            setOutcome("");
                          }
                        }}
                      >
                        Save outcome
                      </button>
                      <button
                        className="text-button"
                        onClick={() => setCompleting(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
                <div className="card-actions">
                  {(record.data.status === "planned" ||
                    record.data.status === "active") && (
                    <button
                      className="text-button"
                      onClick={() => {
                        setCompleting(record);
                        setOutcome(record.data.outcome);
                      }}
                    >
                      <Check size={13} /> Complete experiment
                    </button>
                  )}
                  {(record.data.status === "planned" ||
                    record.data.status === "active") && (
                    <button
                      className="text-button"
                      onClick={() => update(record, { status: "dropped" })}
                    >
                      <X size={13} /> Drop experiment
                    </button>
                  )}
                  <button
                    className="text-button"
                    onClick={() => openForm(record)}
                  >
                    <Edit3 size={13} /> Edit experiment
                  </button>
                  <ConfirmDelete
                    label="experiment"
                    onDelete={async () => {
                      await api(`/insights/records/${record.id}`, {
                        method: "DELETE",
                      });
                      await load();
                    }}
                  />
                </div>
              </article>
            ))}
          </div>
          {error && !editing && (
            <p role="alert" className="error-message">
              {error}
            </p>
          )}
        </section>
      ) : (
        <section className="feature-section weekly-letter">
          <div className="letter-compose">
            <div>
              <span className="eyebrow">SEVEN DAYS, HELD LIGHTLY</span>
              <h2>A letter from your week.</h2>
              <p>
                DreamLit looks for one recurrence, a change or exception when
                the evidence supports it, positive experiences, and a question
                to carry forward.
              </p>
            </div>
            <div className="week-control">
              <label>
                Week ending
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                />
              </label>
              <small>
                {end ? formatPeriod(start, end) : "Choose a week ending date"}
              </small>
              <GenerateInsight
                disabled={!end}
                kind="weekly"
                provider={provider}
                dateFrom={start}
                dateTo={end}
                label="Write weekly letter"
                onCreated={(run) => setLetters((items) => [run, ...items])}
              />
            </div>
          </div>
          {!loading && !letters.length && (
            <EmptyState icon={<Mail />} title="No letters yet">
              Choose a week, then ask DreamLit to gather only what the sources
              can support.
            </EmptyState>
          )}
          <div className="letters-stack">
            {letters.map((letter) => (
              <div className="letter-wrap" key={letter.id}>
                <div className="letter-date">
                  {letter.scope.date_from && letter.scope.date_to
                    ? formatPeriod(letter.scope.date_from, letter.scope.date_to)
                    : new Date(letter.created_at).toLocaleDateString()}
                </div>
                <InsightResult run={letter} onDream={onDream} />
              </div>
            ))}
          </div>
          {error && (
            <p role="alert" className="error-message">
              {error}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
