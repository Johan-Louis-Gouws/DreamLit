import { useEffect, useState } from "react";
import { Edit3, Plus, UserRound } from "lucide-react";
import { api, json } from "../../api";
import type { InsightRun, Provider } from "../../types";
import type { PersonData, PersonRecord } from "./types";
import {
  ConfirmDelete,
  EmptyState,
  GenerateInsight,
  InsightResult,
  StatusPill,
} from "./shared";

const blank: PersonData = {
  name: "",
  aliases: [],
  relationship: "",
  notes: "",
  include_in_analysis: true,
};

export function People({
  provider,
  onDream,
}: {
  provider: Provider;
  onDream: (id: string) => void;
}) {
  const [people, setPeople] = useState<PersonRecord[]>([]);
  const [runs, setRuns] = useState<InsightRun[]>([]);
  const [editing, setEditing] = useState<PersonRecord | null | "new">(null);
  const [data, setData] = useState<PersonData>(blank);
  const [aliases, setAliases] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const load = async () => {
    const [records, portraits] = await Promise.all([
      api<PersonRecord[]>("/insights/records?kind=person"),
      api<InsightRun[]>("/insights/runs?kind=portrait"),
    ]);
    setPeople(records);
    setRuns(portraits);
    setLoading(false);
  };
  useEffect(() => {
    load().catch((e) => {
      setError(String(e));
      setLoading(false);
    });
  }, []);
  function openForm(person?: PersonRecord) {
    setEditing(person || "new");
    setData(person ? { ...person.data } : blank);
    setAliases(person?.data.aliases.join(", ") || "");
    setError("");
  }
  async function save() {
    if (saving) return;
    setSaving(true);
    setError("");
    const payload = {
      ...data,
      aliases: aliases
        .split(/[\n,]/)
        .map((item) => item.trim())
        .filter(Boolean),
    };
    try {
      if (editing && editing !== "new")
        await api(
          `/insights/records/${editing.id}`,
          json("PUT", { expected_revision: editing.revision, data: payload }),
        );
      else
        await api(
          "/insights/records",
          json("POST", { kind: "person", data: payload }),
        );
      setEditing(null);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }
  return (
    <section className="feature-section" aria-label="People">
      <div className="section-lead">
        <div>
          <span className="eyebrow">PEOPLE IN YOUR INNER LANDSCAPE</span>
          <h2>Keep your own context close.</h2>
          <p>
            Names, relationships, and notes stay in your words. Portraits
            describe your experience and never claim to know another person's
            intentions.
          </p>
        </div>
        <button className="secondary" onClick={() => openForm()}>
          <Plus size={15} /> Add a person
        </button>
      </div>
      {editing && (
        <div
          className="record-form paper-form"
          aria-label={
            editing === "new" ? "Add person" : `Edit ${editing.data.name}`
          }
        >
          <div className="card-top">
            <span className="eyebrow">
              {editing === "new"
                ? "A PERSON YOU DREAM ABOUT"
                : "REVISE YOUR CONTEXT"}
            </span>
            <button className="text-button" onClick={() => setEditing(null)}>
              Cancel
            </button>
          </div>
          <div className="form-grid">
            <label>
              Name
              <input
                value={data.name}
                onChange={(e) => setData({ ...data, name: e.target.value })}
              />
            </label>
            <label>
              Aliases
              <input
                value={aliases}
                onChange={(e) => setAliases(e.target.value)}
                placeholder="Separate with commas"
              />
            </label>
            <label className="wide">
              Relationship
              <textarea
                value={data.relationship}
                onChange={(e) =>
                  setData({ ...data, relationship: e.target.value })
                }
              />
            </label>
            <label className="wide">
              Personal notes
              <textarea
                value={data.notes}
                onChange={(e) => setData({ ...data, notes: e.target.value })}
              />
            </label>
          </div>
          <label className="checkbox paper-checkbox">
            <input
              type="checkbox"
              checked={data.include_in_analysis}
              onChange={(e) =>
                setData({ ...data, include_in_analysis: e.target.checked })
              }
            />{" "}
            Include this person in analysis and portraits
          </label>
          <button
            className="primary"
            disabled={saving || !data.name.trim()}
            onClick={save}
          >
            {editing === "new" ? "Save person" : "Save changes"}
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
          <span className="status-dot" /> Gathering people…
        </p>
      )}
      {!loading && !people.length && !editing && (
        <EmptyState icon={<UserRound />} title="No one added yet">
          Add someone when their presence matters to your dreams or reflections.
        </EmptyState>
      )}
      <div className="record-stack">
        {people.map((person) => {
          const portrait = runs.find((run) => run.subject_id === person.id);
          return (
            <article
              className="record-card person-card"
              key={person.id}
              aria-label={`Person: ${person.data.name}`}
            >
              <div className="card-top">
                <div>
                  <span className="record-kicker">
                    PERSON · REVISION {person.revision}
                  </span>
                  <h3>{person.data.name}</h3>
                </div>
                <StatusPill
                  tone={
                    person.data.include_in_analysis ? "current" : "excluded"
                  }
                >
                  {person.data.include_in_analysis
                    ? "Included"
                    : "Private from analysis"}
                </StatusPill>
              </div>
              {!!person.data.aliases.length && (
                <p className="aliases">
                  Also: {person.data.aliases.join(", ")}
                </p>
              )}
              {person.data.relationship && <p>{person.data.relationship}</p>}
              {person.data.notes && (
                <div className="personal-note">
                  <span>YOUR NOTE</span>
                  {person.data.notes}
                </div>
              )}
              <div className="card-actions">
                <GenerateInsight
                  disabled={!person.data.include_in_analysis}
                  kind="portrait"
                  provider={provider}
                  subjectId={person.id}
                  label={
                    portrait?.stale
                      ? "Regenerate portrait"
                      : "Generate portrait"
                  }
                  onCreated={(run) =>
                    setRuns((items) => [
                      run,
                      ...items.filter((item) => item.id !== run.id),
                    ])
                  }
                />
                <button
                  className="text-button"
                  onClick={() => openForm(person)}
                >
                  <Edit3 size={13} /> Edit person
                </button>
                <ConfirmDelete
                  label="person"
                  onDelete={async () => {
                    await api(`/insights/records/${person.id}`, {
                      method: "DELETE",
                    });
                    await load();
                  }}
                />
              </div>
              {portrait && <InsightResult run={portrait} onDream={onDream} />}
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
  );
}
