import { useEffect, useState } from "react";
import { Orbit, List, ArrowUpRight, Sparkles } from "lucide-react";
import { api, json } from "../../api";
import type { GraphData, GraphNode, Job, Provider } from "../../types";
import { Constellation } from "./Constellation";
import { JobProgress } from "../../JobProgress";

export function ConnectionsView({
  provider,
  onDream,
  onPattern,
  refresh,
}: {
  provider: Provider;
  onDream: (id: string) => void;
  onPattern: (id: string) => void;
  refresh: number;
}) {
  const [graph, setGraph] = useState<GraphData>({
      nodes: [],
      edges: [],
      scope: {
        included_dream_ids: [],
        total_eligible_dreams: 0,
        truncated: false,
      },
    }),
    [list, setList] = useState(false),
    [kind, setKind] = useState(""),
    [from, setFrom] = useState(""),
    [to, setTo] = useState(""),
    [job, setJob] = useState<Job | null>(null),
    [shared, setShared] = useState<GraphNode | null>(null),
    [error, setError] = useState("");
  const load = () => {
    const params = new URLSearchParams();
    if (kind) params.set("kind", kind);
    if (from) params.set("date_from", from);
    if (to) params.set("date_to", to);
    return api<GraphData>("/graph?" + params).then(setGraph);
  };
  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [refresh, kind, from, to]);
  const select = (node: GraphNode) => {
    setShared(null);
    if (node.pattern_id) onPattern(node.pattern_id);
    else if (node.dream_id) onDream(node.dream_id);
    else {
      setShared(node);
    }
  };
  const patterns = graph.nodes.filter((n) => n.kind === "theme");
  return (
    <section className="page-enter">
      <div className="section-title">
        <div>
          <div className="eyebrow">THE BIGGER PICTURE</div>
          <h1>
            Find the <em>thread.</em>
          </h1>
          <p>Different nights. Familiar feelings. See what connects them.</p>
        </div>
        <button
          className="secondary"
          disabled={
            graph.scope.total_eligible_dreams < 2 ||
            job?.state === "running" ||
            job?.state === "queued"
          }
          onClick={async () => {
            try {
              setError("");
              setJob(
                await api<Job>(
                  "/scan",
                  json("POST", {
                    provider,
                    date_from: from || null,
                    date_to: to || null,
                  }),
                ),
              );
            } catch (e) {
              setError(String(e));
            }
          }}
        >
          <Sparkles size={15} /> Scan history
        </button>
      </div>
      <div className="map-toolbar">
        <div className="segmented">
          <button
            className={!list ? "active" : ""}
            onClick={() => setList(false)}
          >
            <Orbit size={15} /> Constellation
          </button>
          <button
            className={list ? "active" : ""}
            onClick={() => setList(true)}
          >
            <List size={15} /> Timeline
          </button>
        </div>
        <div className="map-filters">
          <select
            aria-label="Connection type"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            <option value="">All connections</option>
            <option value="theme">Themes</option>
            <option value="character">Characters</option>
            <option value="place">Places</option>
          </select>
          <input
            aria-label="From date"
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
          <span>—</span>
          <input
            aria-label="To date"
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </div>
      </div>
      {job && (
        <JobProgress
          onUpdate={setJob}
          key={job.id}
          initial={job}
          provider={provider}
          onDone={() => {
            load().catch((e) => setError(String(e)));
          }}
        />
      )}
      {error && (
        <p role="alert" className="error-message">
          {error}
        </p>
      )}
      {shared && (
        <section className="context-note" aria-label="Shared dream detail">
          <button
            className="text-button float-right"
            onClick={() => setShared(null)}
          >
            Close detail
          </button>
          <div className="eyebrow">RECURRING {shared.kind.toUpperCase()}</div>
          <h3>{shared.label}</h3>
          <p>
            The same label appears in these dreams. You decide whether it refers
            to the same person or place.
          </p>
          {shared.evidence?.map((ref, i) => (
            <div className="evidence-quote" key={i}>
              <blockquote>{ref.quote}</blockquote>
              <button onClick={() => onDream(ref.dream_id)}>
                Open dream <ArrowUpRight size={13} />
              </button>
            </div>
          ))}
        </section>
      )}
      {!list ? (
        <div className="map-frame">
          <Constellation graph={graph} onSelect={select} />
          {!graph.nodes.length && (
            <div className="map-empty">
              <Orbit size={32} />
              <h2>Your constellation is waiting.</h2>
              <p>
                Save a dream to create your first point.
                <br />
                Connections emerge as your diary grows.
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="connection-list">
          {[...graph.nodes]
            .sort((a, b) => (b.date || "").localeCompare(a.date || ""))
            .map((node) => (
              <button key={node.id} onClick={() => select(node)}>
                <span className={`legend-dot ${node.kind}`} />
                <div>
                  <small>{node.date || node.kind}</small>
                  <p>{node.label}</p>
                </div>
                <ArrowUpRight size={17} />
              </button>
            ))}
        </div>
      )}
      <div className="map-legend">
        <span>
          <i className="legend-dot dream" />
          Dream
        </span>
        <span>
          <i className="legend-dot theme" />
          Possible theme
        </span>
        <span>
          <i className="legend-line" />
          Shared label
        </span>
        <span>
          <i className="legend-line inferred" />
          Suggested connection
        </span>
        <strong>
          {graph.scope.included_dream_ids.length}{" "}
          {graph.scope.included_dream_ids.length === 1 ? "dream" : "dreams"} · {patterns.length}{" "}
          {patterns.length === 1 ? "theme" : "themes"}
        </strong>
      </div>
      {patterns.length > 0 && (
        <div className="pattern-cards">
          {patterns.slice(0, 6).map((node, i) => (
            <button key={node.id} onClick={() => select(node)}>
              <span className="eyebrow">
                THREAD {String(i + 1).padStart(2, "0")}
              </span>
              <h3>{node.label}</h3>
              <span className="text-button">
                Explore the evidence <ArrowUpRight size={15} />
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
