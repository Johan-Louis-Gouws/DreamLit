import { useEffect, useState } from "react";
import { LoaderCircle, Check, RotateCcw, X } from "lucide-react";
import { api, json } from "./api";
import type { Job, Provider } from "./types";

export function JobProgress({
  initial,
  provider,
  onDone,
  onUpdate,
}: {
  initial: Job;
  provider: Provider;
  onDone: (job: Job) => void;
  onUpdate?: (job: Job) => void;
}) {
  const [job, setJob] = useState(initial);
  const [error, setError] = useState("");
  useEffect(() => {
    setJob(initial);
  }, [initial.id]);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await api<Job>(`/jobs/${job.id}`);
        if (!active) return;
        setJob(next);
        onUpdate?.(next);
        if (next.state === "queued" || next.state === "running")
          timer = setTimeout(poll, 1800);
        else onDone(next);
      } catch (e) {
        if (active) setError(String(e));
      }
    };
    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [job.id]);
  const running = job.state === "queued" || job.state === "running";
  return (
    <div className={`job-status ${job.state}`} role="status">
      {running ? (
        <LoaderCircle size={17} className="spin" />
      ) : job.state === "completed" ? (
        <Check size={17} />
      ) : (
        <span className="status-dot" />
      )}
      <div>
        <strong>{job.stage}</strong>
        {error && <small>{error}</small>}
      </div>
      {running ? (
        <button
          className="icon-button"
          aria-label="Cancel job"
          onClick={async () => {
            try {
              const next = await api<Job>(`/jobs/${job.id}/cancel`, {
                method: "POST",
              });
              setJob(next);
              onUpdate?.(next);
            } catch (e) {
              setError(String(e));
            }
          }}
        >
          <X size={16} />
        </button>
      ) : (
        (job.state === "failed" || job.state === "cancelled") && (
          <button
            className="text-button"
            onClick={async () => {
              try {
                setError("");
                const next = await api<Job>(
                  `/jobs/${job.id}/retry`,
                  json("POST", { provider: job.provider || provider }),
                );
                setJob(next);
                onUpdate?.(next);
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            <RotateCcw size={14} /> Retry
          </button>
        )
      )}
    </div>
  );
}
