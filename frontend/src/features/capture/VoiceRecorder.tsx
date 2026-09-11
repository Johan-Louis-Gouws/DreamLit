import { useEffect, useRef, useState } from "react";
import { Mic, Square, Upload, Download } from "lucide-react";
import { api } from "../../api";
import type { Dream } from "../../types";

export function VoiceRecorder({
  date,
  onSaved,
  onError,
}: {
  date: string;
  onSaved: (d: Dream) => void;
  onError: (s: string) => void;
}) {
  const recorder = useRef<MediaRecorder | null>(null),
    stream = useRef<MediaStream | null>(null),
    chunks = useRef<Blob[]>([]);
  const [recording, setRecording] = useState(false),
    [seconds, setSeconds] = useState(0),
    [blob, setBlob] = useState<Blob | null>(null),
    [url, setUrl] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(
    () => () => {
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
    },
    [],
  );
  useEffect(() => {
    if (!recording) return;
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [recording]);
  useEffect(() => {
    if (!blob) {
      setUrl("");
      return;
    }
    const next = URL.createObjectURL(blob);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [blob]);
  async function start() {
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      const mime = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((t) => MediaRecorder.isTypeSupported(t));
      const next = new MediaRecorder(
        stream.current,
        mime ? { mimeType: mime } : undefined,
      );
      recorder.current = next;
      chunks.current = [];
      next.ondataavailable = (e) => {
        if (e.data.size) chunks.current.push(e.data);
      };
      next.onstop = () => {
        setBlob(new Blob(chunks.current, { type: next.mimeType }));
        setRecording(false);
        stream.current?.getTracks().forEach((t) => t.stop());
      };
      next.onerror = () => {
        onError(
          "Recording stopped unexpectedly. You can import a note or write your dream.",
        );
        if (next.state !== "inactive") next.stop();
        stream.current?.getTracks().forEach((t) => t.stop());
        setRecording(false);
      };
      setSeconds(0);
      setBlob(null);
      next.start(1000);
      setRecording(true);
    } catch {
      stream.current?.getTracks().forEach((t) => t.stop());
      onError(
        "Microphone access is unavailable. Allow microphone access, import a recording, or write your dream.",
      );
    }
  }
  async function save() {
    if (!blob) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", blob, "dream-recording");
      form.append("dreamed_on", date);
      const dream = await api<Dream>("/audio", { method: "POST", body: form });
      setBlob(null);
      onSaved(dream);
    } catch (e) {
      onError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="voice-capture">
      <button
        className={`record-orb ${recording ? "recording" : ""}`}
        aria-label={recording ? "Stop recording" : "Start recording"}
        onClick={() => (recording ? recorder.current?.stop() : start())}
      >
        {recording ? <Square size={28} /> : <Mic size={34} />}
      </button>
      <h3>
        {recording
          ? "Stay with the dream."
          : blob
            ? "A little piece of the night."
            : "Say it before it fades."}
      </h3>
      <p>
        {recording
          ? `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")} · recording`
          : "Fragments, feelings, strange details. All of it belongs here."}
      </p>
      {blob && (
        <div className="recording-preview">
          <audio controls src={url} />
          <div className="button-row">
            <button className="primary" onClick={save} disabled={busy}>
              {busy ? "Saving…" : "Save recording"}
            </button>
            <a className="text-button" href={url} download="dream-note.webm">
              <Download size={15} /> Keep a copy
            </a>
          </div>
        </div>
      )}
      {!recording && (
        <label className="import-button">
          <Upload size={16} /> Import a voice note
          <input
            type="file"
            accept="audio/*,video/webm,video/mp4"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) setBlob(file);
            }}
          />
        </label>
      )}
    </div>
  );
}
