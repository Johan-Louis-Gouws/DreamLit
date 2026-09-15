import { useEffect, useState } from "react";
import {
  Edit3,
  History,
  MessageCircleQuestion,
  Plus,
  Sparkles,
} from "lucide-react";
import { api, json } from "../../api";
import type { Dream, InsightRun, Provider } from "../../types";
import { AnswerVoice } from "./AnswerVoice";
import { People } from "./People";
import type { AnswerData, AnswerRecord, PersonRecord } from "./types";
import {
  ConfirmDelete,
  EmptyState,
  GenerateInsight,
  RecordHistory,
  StatusPill,
  Tabs,
  ViewHeader,
  ContextSources,
} from "./shared";

const starters = [
  ["Right now", "What is asking for your attention?"],
  ["Relationships", "Who has been on your mind lately, and why?"],
  ["Change", "What feels different in your life right now?"],
  ["Needs", "What do you wish there were more room for?"],
];

const blank = (question = "", topic = "General"): AnswerData => ({
  question,
  answer: "",
  topic,
  scope: "current",
  status: "current",
  dream_id: null,
  person_id: null,
  audio_id: null,
});

export function YourWorld({
  provider,
  dreams,
  onDream,
}: {
  provider: Provider;
  dreams: Dream[];
  onDream: (id: string) => void;
}) {
  const [tab, setTab] = useState("questions");
  const [answers, setAnswers] = useState<AnswerRecord[]>([]);
  const [people, setPeople] = useState<PersonRecord[]>([]);
  const [questionRuns, setQuestionRuns] = useState<InsightRun[]>([]);
  const [editing, setEditing] = useState<AnswerRecord | null | "new">(null);
  const [data, setData] = useState<AnswerData>(blank());
  const [history, setHistory] = useState<AnswerRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const load = async () => {
    const [savedAnswers, savedPeople, runs] = await Promise.all([
      api<AnswerRecord[]>("/insights/records?kind=answer"),
      api<PersonRecord[]>("/insights/records?kind=person"),
      api<InsightRun[]>("/insights/runs?kind=question"),
    ]);
    setAnswers(savedAnswers);
    setPeople(savedPeople);
    setQuestionRuns(runs);
    setLoading(false);
  };
  useEffect(() => {
    load().catch((e) => {
      setError(String(e));
      setLoading(false);
    });
  }, [tab]);
  function start(question = "", topic = "General") {
    setEditing("new");
    setData(blank(question, topic));
    setError("");
  }
  function edit(answer: AnswerRecord) {
    setEditing(answer);
    setData({ ...answer.data });
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
        await api("/insights/records", json("POST", { kind: "answer", data }));
      setEditing(null);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }
  async function updateStatus(
    answer: AnswerRecord,
    status: AnswerData["status"],
  ) {
    try {
      await api(
        `/insights/records/${answer.id}`,
        json("PUT", {
          expected_revision: answer.revision,
          data: { ...answer.data, status },
        }),
      );
      await load();
    } catch (e) {
      setError(String(e));
    }
  }
  const latestQuestion = questionRuns[0];
  return (
    <div className="insights-page">
      <ViewHeader
        eyebrow="THE WAKING WORLD"
        title={
          <>
            Your <em>world</em>
          </>
        }
      >
        Optional context, kept in your own words. Answer what feels useful and
        leave the rest untouched.
      </ViewHeader>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "questions", label: "Questions" },
          { id: "people", label: "People" },
        ]}
      />
      {tab === "people" ? (
        <People provider={provider} onDream={onDream} />
      ) : (
        <section className="feature-section">
          <div className="question-intro-grid">
            <div>
              <span className="eyebrow">A PLACE TO BEGIN</span>
              <h2>Small questions. Honest context.</h2>
              <p>
                These answers can help future reflections stay grounded in your
                waking life. Nothing here blocks capture.
              </p>
            </div>
            <div className="starter-list">
              {starters.map(([topic, question], index) => (
                <button key={question} onClick={() => start(question, topic)}>
                  <span>0{index + 1}</span>
                  <div>
                    <small>{topic}</small>
                    {question}
                  </div>
                  <Plus size={14} />
                </button>
              ))}
            </div>
          </div>
          <div className="tailored-question">
            <div>
              <Sparkles size={18} />
              <span>
                <strong>
                  Ask for a question shaped by what you have shared
                </strong>
                <small>
                  The selected CLI sees only eligible saved context and dream
                  sources.
                </small>
              </span>
            </div>
            <GenerateInsight
              kind="question"
              provider={provider}
              label="Suggest a tailored question"
              onCreated={(run) => setQuestionRuns((items) => [run, ...items])}
            />
            {latestQuestion && (
              <div
                className={`suggested-question ${latestQuestion.stale ? "stale" : ""}`}
              >
                <span>
                  {latestQuestion.stale
                    ? "EARLIER QUESTION"
                    : "A QUESTION FOR NOW"}
                </span>
                <p>{latestQuestion.output.question}</p>
                <button
                  className="secondary"
                  onClick={() =>
                    start(latestQuestion.output.question, "Tailored")
                  }
                >
                  Answer this question
                </button>
                <ContextSources
                  sources={
                    latestQuestion.sources.filter(
                      (source) => source.kind !== "dream",
                    ) as import("../../types").PersonalContextSource[]
                  }
                />
              </div>
            )}
          </div>
          {editing && (
            <div
              className="record-form answer-form"
              aria-label={editing === "new" ? "New answer" : "Edit answer"}
            >
              <div className="card-top">
                <span className="eyebrow">
                  {editing === "new" ? "YOUR WORDS" : "REVISE THIS ANSWER"}
                </span>
                <button
                  className="text-button"
                  onClick={() => setEditing(null)}
                >
                  Cancel
                </button>
              </div>
              <label>
                Your question
                <input
                  value={data.question}
                  onChange={(e) =>
                    setData({ ...data, question: e.target.value })
                  }
                />
              </label>
              <label>
                Your answer
                <textarea
                  aria-label="Your answer"
                  value={data.answer}
                  onChange={(e) => setData({ ...data, answer: e.target.value })}
                />
              </label>
              <AnswerVoice
                onAccept={(text, audioId) =>
                  setData({ ...data, answer: text, audio_id: audioId })
                }
              />
              <div className="form-grid compact">
                <label>
                  Topic
                  <input
                    value={data.topic}
                    onChange={(e) =>
                      setData({ ...data, topic: e.target.value })
                    }
                  />
                </label>
                <label>
                  Time scope
                  <select
                    value={data.scope}
                    onChange={(e) =>
                      setData({
                        ...data,
                        scope: e.target.value as AnswerData["scope"],
                      })
                    }
                  >
                    <option value="current">Current</option>
                    <option value="ongoing">Ongoing</option>
                    <option value="dream">This dream</option>
                  </select>
                </label>
                <label>
                  Answer status
                  <select
                    aria-label="Answer status"
                    value={data.status}
                    onChange={(e) =>
                      setData({
                        ...data,
                        status: e.target.value as AnswerData["status"],
                      })
                    }
                  >
                    <option value="current">Current</option>
                    <option value="changed">Changed</option>
                    <option value="excluded">Excluded from analysis</option>
                  </select>
                </label>
                <label>
                  Linked dream
                  <select
                    value={data.dream_id || ""}
                    onChange={(e) =>
                      setData({ ...data, dream_id: e.target.value || null })
                    }
                  >
                    <option value="">None</option>
                    {dreams.map((dream) => (
                      <option value={dream.id} key={dream.id}>
                        {dream.dreamed_on} · {dream.text.slice(0, 42)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Linked person
                  <select
                    value={data.person_id || ""}
                    onChange={(e) =>
                      setData({ ...data, person_id: e.target.value || null })
                    }
                  >
                    <option value="">None</option>
                    {people.map((person) => (
                      <option value={person.id} key={person.id}>
                        {person.data.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button
                className="primary"
                disabled={
                  saving || !data.question.trim() || !data.answer.trim()
                }
                onClick={save}
              >
                {editing === "new" ? "Save answer" : "Save changes"}
              </button>
              {error && (
                <p role="alert" className="error-message">
                  {error}
                </p>
              )}
            </div>
          )}
          <div className="saved-heading">
            <div>
              <span className="eyebrow">SAVED CONTEXT</span>
              <h2>Your answers</h2>
            </div>
            {!editing && (
              <button className="secondary" onClick={() => start()}>
                <Plus size={14} /> Write your own
              </button>
            )}
          </div>
          {loading && (
            <p className="loading-line">
              <span className="status-dot" /> Opening your context…
            </p>
          )}
          {!loading && !answers.length && !editing && (
            <EmptyState
              icon={<MessageCircleQuestion />}
              title="No answers saved"
            >
              Choose a prompt above, ask for a tailored question, or write your
              own.
            </EmptyState>
          )}
          <div className="record-stack">
            {answers.map((answer) => (
              <article
                className={`record-card answer-card ${answer.data.status}`}
                aria-label={`Answer: ${answer.data.question}`}
                key={answer.id}
              >
                <div className="card-top">
                  <div>
                    <span className="record-kicker">
                      {answer.data.topic.toUpperCase()} ·{" "}
                      {new Date(answer.updated_at).toLocaleDateString()}
                    </span>
                    <h3>{answer.data.question}</h3>
                  </div>
                  <StatusPill tone={answer.data.status}>
                    {answer.data.status === "excluded"
                      ? "Excluded"
                      : answer.data.status[0].toUpperCase() +
                        answer.data.status.slice(1)}
                  </StatusPill>
                </div>
                <p className="answer-copy">{answer.data.answer}</p>
                <div className="record-links">
                  {answer.data.dream_id && (
                    <button onClick={() => onDream(answer.data.dream_id!)}>
                      Open linked dream
                    </button>
                  )}
                  {answer.data.person_id && (
                    <span>
                      Linked to{" "}
                      {people.find(
                        (person) => person.id === answer.data.person_id,
                      )?.data.name || "a person"}
                    </span>
                  )}
                  {answer.data.audio_id && <span>Voice answer saved</span>}
                </div>
                <div className="card-actions">
                  <button className="text-button" onClick={() => edit(answer)}>
                    <Edit3 size={13} /> Edit answer
                  </button>
                  <button
                    className="text-button"
                    onClick={() => setHistory(answer)}
                  >
                    <History size={13} /> View history
                  </button>
                  {answer.data.status === "excluded" ? (
                    <button
                      className="text-button"
                      onClick={() => updateStatus(answer, "current")}
                    >
                      Include in analysis
                    </button>
                  ) : (
                    <button
                      className="text-button"
                      onClick={() => updateStatus(answer, "excluded")}
                    >
                      Exclude from analysis
                    </button>
                  )}
                  <ConfirmDelete
                    label="answer"
                    onDelete={async () => {
                      await api(`/insights/records/${answer.id}`, {
                        method: "DELETE",
                      });
                      await load();
                    }}
                  />
                </div>
                {history?.id === answer.id && (
                  <RecordHistory
                    record={answer}
                    onClose={() => setHistory(null)}
                  />
                )}
              </article>
            ))}
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
