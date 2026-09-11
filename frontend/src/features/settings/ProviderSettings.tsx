import { useEffect, useState } from "react";
import { Check, Download, ArrowUpRight, Plus, Trash2 } from "lucide-react";
import { api, json } from "../../api";
import type { Preferences, Association, Job } from "../../types";
import { JobProgress } from "../../JobProgress";

export function ProviderSettings({
  preferences,
  onSaved,
}: {
  preferences: Preferences;
  onSaved: (p: Preferences) => void;
}) {
  const [form, setForm] = useState(preferences),
    [providers, setProviders] = useState<
      Record<
        string,
        {
          installed: boolean;
          version?: string;
          status: string;
          note?: string;
          model?: string;
        }
      >
    >({}),
    [transcription, setTranscription] = useState<{ ready: boolean } | null>(
      null,
    ),
    [error, setError] = useState(""),
    [saved, setSaved] = useState(false),
    [associations, setAssociations] = useState<Association[]>([]),
    [editing, setEditing] = useState<Association | null>(null),
    [label, setLabel] = useState(""),
    [meaning, setMeaning] = useState(""),
    [includeAudio, setIncludeAudio] = useState(true),
    [job, setJob] = useState<Job | null>(null);
  useEffect(() => {
    api<typeof providers>("/providers")
      .then(setProviders)
      .catch((e) => setError(String(e)));
    api<{ ready: boolean }>("/transcription")
      .then(setTranscription)
      .catch(() => {});
    api<Association[]>("/associations")
      .then(setAssociations)
      .catch((e) => setError(String(e)));
  }, []);
  const save = async () => {
    try {
      const next = await api<Preferences>("/settings", json("PUT", form));
      onSaved(next);
      setSaved(true);
      setTranscription(await api("/transcription"));
      return true;
    } catch (e) {
      setError(String(e));
      return false;
    }
  };
  return (
    <section className="settings-page page-enter">
      <div className="section-title">
        <div>
          <div className="eyebrow">MAKE IT YOURS</div>
          <h1>
            A space for <em>you.</em>
          </h1>
          <p>Your journal, your context, your choice of guide.</p>
        </div>
      </div>
      <section className="settings-section">
        <div>
          <span className="eyebrow">01 / ANALYSIS</span>
          <h3>Choose your guide</h3>
          <p>
            The journal is stored on this computer. Analysis sends selected
            dream content through your chosen CLI to its provider.
          </p>
        </div>
        <div>
          <div className="provider-options">
            {(["codex", "claude"] as const).map((provider) => (
              <button
                key={provider}
                className={form.provider === provider ? "selected" : ""}
                onClick={() => {
                  setForm({ ...form, provider });
                  setSaved(false);
                }}
              >
                <span className="provider-mark">
                  {provider === "codex" ? "✧" : "✳"}
                </span>
                <strong>{provider === "codex" ? "Codex" : "Claude"}</strong>
                <small>
                  {providers[provider]?.version ||
                    (providers[provider]
                      ? providers[provider].installed ? "Installed" : "Not installed"
                      : "Checking installation…")}
                </small>
                {form.provider === provider && <Check size={17} />}
              </button>
            ))}
          </div>
          <label className="field-label">
            Codex model override
            <input
              value={form.codex_model}
              placeholder={providers.codex?.model || "Use CLI model preference"}
              onChange={(e) => {
                setForm({ ...form, codex_model: e.target.value });
                setSaved(false);
              }}
            />
          </label>
          <label className="field-label">
            Claude model override
            <input
              value={form.claude_model}
              placeholder="Use CLI model preference"
              onChange={(e) => {
                setForm({ ...form, claude_model: e.target.value });
                setSaved(false);
              }}
            />
          </label>
          <p className="small muted">
            Leave overrides empty to preserve CLI model preferences. Providers
            are never switched automatically.
          </p>
          <button
            className="text-button"
            onClick={async () => {
              try {
                if (!(await save())) return;
                setJob(
                  await api<Job>(`/providers/${form.provider}/check`, {
                    method: "POST",
                  }),
                );
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            Test {form.provider} connection <ArrowUpRight size={15} />
          </button>
          {job && (
            <JobProgress
              onUpdate={setJob}
              key={job.id}
              initial={job}
              provider={form.provider}
              onDone={() => {}}
            />
          )}
        </div>
      </section>
      <section className="settings-section">
        <div>
          <span className="eyebrow">02 / VOICE NOTES</span>
          <h3>Keep the original voice</h3>
          <p>
            Transcription runs locally. You review the words before a dream is
            analysed.
          </p>
          <span
            className={`setup-status ${transcription?.ready ? "ready" : ""}`}
          >
            {transcription?.ready
              ? "● Local transcription ready"
              : "○ Local transcription needs setup"}
          </span>
        </div>
        <div>
          <label className="field-label">
            whisper.cpp command
            <input
              value={form.whisper_binary}
              placeholder="/path/to/whisper-cli"
              onChange={(e) => {
                setForm({ ...form, whisper_binary: e.target.value });
                setSaved(false);
              }}
            />
          </label>
          <label className="field-label">
            Whisper model file
            <input
              value={form.whisper_model}
              placeholder="/path/to/ggml-base.en.bin"
              onChange={(e) => {
                setForm({ ...form, whisper_model: e.target.value });
                setSaved(false);
              }}
            />
          </label>
          <label className="field-label">
            FFmpeg command
            <input
              value={form.ffmpeg_binary}
              onChange={(e) => {
                setForm({ ...form, ffmpeg_binary: e.target.value });
                setSaved(false);
              }}
            />
          </label>
          <p className="small muted">
            The local setup command in the README installs the transcription
            tool and model. Recordings can be saved before setup is complete.
          </p>
        </div>
      </section>
      <div className="settings-save">
        <button className="primary" onClick={save}>
          {saved ? (
            <>
              <Check size={16} /> Settings saved
            </>
          ) : (
            "Save settings"
          )}
        </button>
      </div>
      <section className="settings-section">
        <div>
          <span className="eyebrow">03 / PERSONAL CONTEXT</span>
          <h3>Your own meanings</h3>
          <p>
            A place or a person means something different to everyone. Give your
            dreams a little waking-life context.
          </p>
        </div>
        <div>
          <label className="field-label">
            Person, place, or recurring detail
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="My childhood home"
            />
          </label>
          <label className="field-label">
            What does it mean to you?
            <textarea
              value={meaning}
              onChange={(e) => setMeaning(e.target.value)}
              placeholder="A place where I felt…"
            />
          </label>
          <button
            className="secondary"
            disabled={!label.trim() || !meaning.trim()}
            onClick={async () => {
              try {
                await api(
                  editing ? `/associations/${editing.id}` : "/associations",
                  json(editing ? "PUT" : "POST", {
                    label,
                    meaning,
                    dream_id: editing?.dream_id || null,
                  }),
                );
                setLabel("");
                setMeaning("");
                setEditing(null);
                setAssociations(await api("/associations"));
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            <Plus size={15} />{" "}
            {editing ? "Save association" : "Add association"}
          </button>
          <div className="association-list">
            {associations.map((a) => (
              <div key={a.id}>
                <strong>{a.label}</strong>
                <p>{a.meaning}</p>
                <button
                  className="text-button"
                  onClick={() => {
                    setEditing(a);
                    setLabel(a.label);
                    setMeaning(a.meaning);
                  }}
                >
                  Edit association
                </button>
                <button
                  className="icon-button"
                  aria-label={`Delete association ${a.label}`}
                  onClick={async () => {
                    try {
                      await api(`/associations/${a.id}`, { method: "DELETE" });
                      setAssociations(await api("/associations"));
                      if (editing?.id === a.id) {
                        setEditing(null);
                        setLabel("");
                        setMeaning("");
                      }
                    } catch (e) {
                      setError(String(e));
                    }
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="settings-section">
        <div>
          <span className="eyebrow">04 / YOUR JOURNAL</span>
          <h3>Take it with you</h3>
          <p>
            Export entries, original versions, associations, and reflections in
            a portable archive.
          </p>
        </div>
        <div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={includeAudio}
              onChange={(e) => setIncludeAudio(e.target.checked)}
            />{" "}
            Include original recordings
          </label>
          <button
            className="secondary"
            onClick={async () => {
              try {
                const response = await fetch(
                  "/api/export",
                  json("POST", { include_audio: includeAudio }),
                );
                if (!response.ok) throw new Error("Export failed");
                const url = URL.createObjectURL(await response.blob());
                const a = document.createElement("a");
                a.href = url;
                a.download = "dreamlit-journal.zip";
                a.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            <Download size={15} /> Export journal
          </button>
        </div>
      </section>
      {error && (
        <p role="alert" className="error-message">
          {error}
        </p>
      )}
    </section>
  );
}
