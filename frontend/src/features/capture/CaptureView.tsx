import { useState } from "react";
import { ArrowUpRight, Feather, Mic, Moon, Plus, Check } from "lucide-react";
import { api, json, today, dateLabel } from "../../api";
import type { Dream } from "../../types";
import { VoiceRecorder } from "./VoiceRecorder";

export function CaptureView({
  onSaved,
  onOpen,
  count,
}: {
  onSaved: (d: Dream) => void;
  onOpen: (id: string) => void;
  count: number;
}) {
  const [mode, setMode] = useState<"write" | "voice">("write"),
    [text, setText] = useState(""),
    [context, setContext] = useState(""),
    [date, setDate] = useState(today()),
    [extra, setExtra] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [saved, setSaved] = useState<Dream | null>(null);
  const complete = (dream: Dream) => {
    setSaved(dream);
    setText("");
    setContext("");
    onSaved(dream);
  };
  async function save() {
    setError("");
    setBusy(true);
    try {
      complete(
        await api<Dream>(
          "/dreams",
          json("POST", { dreamed_on: date, text, context }),
        ),
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="capture-page page-enter">
      <section className="capture-intro">
        <div>
          <div className="eyebrow">
            <span className="tiny-star">✦</span> A PLACE FOR YOUR INNER WORLD
          </div>
          <h1>
            Every dream
            <br />
            leaves a <em>thread.</em>
          </h1>
          <p>
            Catch what you remember.
            <br />
            Discover what keeps finding its way back.
          </p>
        </div>
        <div className="orbital-art" aria-hidden="true">
          <div className="orbit-ring ring-one" />
          <div className="orbit-ring ring-two" />
          <div className="orbit-ring ring-three" />
          <div className="moon-disc" />
          <i className="star s-one">✧</i>
          <i className="star s-two">✦</i>
          <i className="star s-three">·</i>
          <span className="orbit-caption">THE NIGHT HAS SOMETHING TO SAY</span>
        </div>
      </section>
      <section className="capture-layout">
        <div className="journal-paper">
          <div className="paper-header">
            <div className="mode-switch">
              <button
                className={mode === "write" ? "active" : ""}
                onClick={() => setMode("write")}
              >
                <Feather size={15} /> Write a dream
              </button>
              <button
                className={mode === "voice" ? "active" : ""}
                onClick={() => setMode("voice")}
              >
                <Mic size={15} /> Voice note
              </button>
            </div>
            <label className="date-input">
              <span className="sr-only">Dream date</span>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
          </div>
          {mode === "write" ? (
            <>
              <label className="sr-only" htmlFor="dream-text">
                What do you remember?
              </label>
              <textarea
                id="dream-text"
                className="dream-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="What do you remember?"
                maxLength={50000}
              />
              <div className="capture-footer">
                <button
                  className="context-toggle"
                  onClick={() => setExtra(!extra)}
                >
                  <Plus size={15} /> Add waking-life context
                </button>
                <span>
                  {text.trim()
                    ? `${text.trim().split(/\s+/).length} words`
                    : "A fragment is enough."}
                </span>
              </div>
              {extra && (
                <label className="context-box">
                  What has been on your mind?
                  <textarea
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    placeholder="Optional. Something happening in your life, or what this dream reminds you of."
                  />
                </label>
              )}
              <div className="save-row">
                <span>
                  <Moon size={13} /> Yours to return to.
                </span>
                <button
                  className="primary"
                  disabled={busy || !text.trim() || !date}
                  onClick={save}
                >
                  {busy ? "Saving…" : "Save dream"}
                  <ArrowUpRight size={17} />
                </button>
              </div>
            </>
          ) : (
            <VoiceRecorder date={date} onSaved={complete} onError={setError} />
          )}
          {error && (
            <p role="alert" className="error-message">
              {error}
            </p>
          )}
          {saved && (
            <div className="save-confirmation" role="status">
              <Check size={16} />
              <span>Dream saved</span>
              <button onClick={() => onOpen(saved.id)}>
                Open entry <ArrowUpRight size={14} />
              </button>
            </div>
          )}
        </div>
        <aside className="capture-aside">
          <div className="eyebrow">BEGIN WITH WHAT STAYED</div>
          <span className="aside-index">01 /</span>
          <h3>
            A feeling.
            <br />A face.
            <br />
            An impossible place.
          </h3>
          <p>
            You don’t need the whole story. Small details become meaningful when
            you see them together.
          </p>
          <div className="aside-bottom">
            <span className="tiny-star">✦</span>
            <span>
              {count === 0
                ? "Your first thread starts here."
                : `${count} ${count === 1 ? "dream" : "dreams"} in your growing constellation.`}
            </span>
          </div>
        </aside>
      </section>
      <div className="page-footnote">
        <span>REMEMBER FIRST. UNDERSTAND OVER TIME.</span>
        <span>{dateLabel(today())}</span>
      </div>
    </div>
  );
}
