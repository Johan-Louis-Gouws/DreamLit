import { useEffect, useRef, useState } from "react";
import { Mic, Square, Upload } from "lucide-react";
import { api } from "../../api";
import { JobProgress } from "../../JobProgress";
import type { Job } from "../../types";
import "./voice.css";

interface VoiceNote {
  id: string;
  audio_id: string;
  text: string;
  created_at: string;
  job: Job | null;
}

export function AnswerVoice({
  onAccept,
}: {
  onAccept: (text: string, audioId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [recording, setRecording] = useState(false);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [preview, setPreview] = useState("");
  const [note, setNote] = useState<VoiceNote | null>(null);
  const [notes, setNotes] = useState<VoiceNote[]>([]);
  const [text, setText] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);
  useEffect(() => {
    if (!blob) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(blob);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [blob]);
  useEffect(() => {
    if (open)
      api<VoiceNote[]>("/insights/voice")
        .then(setNotes)
        .catch((e) => setError(String(e)));
  }, [open]);
  const working = busy || job?.state === "queued" || job?.state === "running";

  function choose(saved: VoiceNote) {
    setBlob(null);
    setNote(saved);
    setText(saved.text);
    setJob(saved.job);
    setError("");
  }
  async function startRecording() {
    try {
      setError("");
      if (
        !navigator.mediaDevices?.getUserMedia ||
        typeof MediaRecorder === "undefined"
      ) {
        throw new Error(
          "Recording is unavailable in this browser. Import a voice note or type your answer.",
        );
      }
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      const mime = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const next = new MediaRecorder(
        media,
        mime ? { mimeType: mime } : undefined,
      );
      const chunks: Blob[] = [];
      next.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      next.onstop = () => {
        media.getTracks().forEach((t) => t.stop());
        if (mounted.current) {
          setBlob(new Blob(chunks, { type: next.mimeType }));
          setRecording(false);
        }
      };
      next.onerror = () => {
        media.getTracks().forEach((t) => t.stop());
        if (mounted.current) {
          setRecording(false);
          setError(
            "Recording stopped unexpectedly. You can import a note or type your answer.",
          );
        }
      };
      recorder.current = next;
      setNote(null);
      setJob(null);
      setBlob(null);
      next.start(1000);
      setRecording(true);
    } catch (e) {
      stream.current?.getTracks().forEach((t) => t.stop());
      setError(String(e));
    }
  }
  async function saveRecording() {
    if (!blob) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", blob, "answer-recording");
      const saved = await api<VoiceNote>("/insights/voice", {
        method: "POST",
        body: form,
      });
      choose(saved);
      setNotes((items) => [saved, ...items]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function transcribe() {
    if (!note) return;
    setBusy(true);
    setError("");
    try {
      setJob(
        await api<Job>(`/insights/voice/${note.id}/transcribe`, {
          method: "POST",
        }),
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="answer-voice">
      <button
        type="button"
        className="text-button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        disabled={recording}
      >
        <Mic size={15} />{" "}
        {open ? "Close voice answer" : "Answer with a voice note"}
      </button>
      {open && (
        <div className="answer-voice-content">
          <p className="small muted">
            Save a recording, transcribe it on this computer, then review the
            words before adding them to your answer.
          </p>
          <div className="button-row">
            <button
              type="button"
              className="secondary"
              disabled={working}
              onClick={() =>
                recording ? recorder.current?.stop() : startRecording()
              }
            >
              {recording ? <Square size={15} /> : <Mic size={15} />}{" "}
              {recording ? "Stop answer recording" : "Record an answer"}
            </button>
            {!recording && (
              <label className="text-button voice-import">
                <Upload size={15} /> Import answer recording
                <input
                  type="file"
                  aria-label="Import answer recording"
                  accept="audio/*,video/webm,video/mp4"
                  disabled={working}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setBlob(file);
                      setNote(null);
                      setJob(null);
                      setError("");
                    }
                    e.target.value = "";
                  }}
                />
              </label>
            )}
          </div>
          {recording && <p role="status">Recording your answer…</p>}
          {blob && (
            <div>
              <audio
                controls
                src={preview}
                aria-label="Preview answer recording"
              />
              <button
                type="button"
                className="secondary"
                onClick={saveRecording}
                disabled={working}
              >
                Save answer recording
              </button>
            </div>
          )}
          {note && (
            <div>
              <p className="small">Original recording saved.</p>
              <audio
                controls
                src={`/api/audio/${note.audio_id}`}
                aria-label="Saved answer recording"
              />
              <button
                type="button"
                className="secondary"
                disabled={working}
                onClick={transcribe}
              >
                Transcribe answer locally
              </button>
            </div>
          )}
          {job && (
            <JobProgress
              initial={job}
              provider="codex"
              onUpdate={setJob}
              onDone={async (done) => {
                if (done.state === "completed" && note) {
                  try {
                    const saved = await api<VoiceNote>(
                      `/insights/voice/${note.id}`,
                    );
                    setNote(saved);
                    setText(saved.text);
                  } catch (e) {
                    setError(String(e));
                  }
                }
              }}
            />
          )}
          {!!note?.text && (
            <div className="voice-transcript">
              <label>
                Review answer transcript
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  maxLength={10000}
                />
              </label>
              <button
                type="button"
                className="secondary"
                disabled={!text.trim() || working}
                onClick={() => {
                  onAccept(text.trim(), note.audio_id);
                  setOpen(false);
                }}
              >
                Use reviewed answer
              </button>
            </div>
          )}
          {notes.length > 0 && !recording && (
            <label className="voice-library">
              Saved recordings
              <select
                aria-label="Saved recordings"
                value={note?.id || ""}
                disabled={working}
                onChange={(e) => {
                  const saved = notes.find(
                    (item) => item.id === e.target.value,
                  );
                  if (saved) choose(saved);
                }}
              >
                <option value="">Choose a recording</option>
                {notes.map((saved) => (
                  <option key={saved.id} value={saved.id}>
                    {new Date(saved.created_at).toLocaleString()} ·{" "}
                    {saved.text ? "Transcribed" : "Recording"}
                  </option>
                ))}
              </select>
            </label>
          )}
          {error && (
            <p role="alert" className="error-message">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
