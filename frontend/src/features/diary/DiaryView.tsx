import { Search, ArrowUpRight, Moon, Mic } from "lucide-react";
import { useState } from "react";
import { dateLabel } from "../../api";
import type { Dream } from "../../types";

export function DiaryView({
  dreams,
  onOpen,
  onCapture,
}: {
  dreams: Dream[];
  onOpen: (id: string) => void;
  onCapture: () => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = dreams.filter((d) =>
    (d.text + " " + d.context).toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <section className="page-enter">
      <div className="section-title">
        <div>
          <div className="eyebrow">YOUR NIGHT ARCHIVE</div>
          <h1>
            The dream <em>diary.</em>
          </h1>
          <p>A record of the places your mind goes.</p>
        </div>
        <button className="primary" onClick={onCapture}>
          New dream <ArrowUpRight size={16} />
        </button>
      </div>
      <div className="list-toolbar">
        <span>
          {dreams.length} {dreams.length === 1 ? "entry" : "entries"}
        </span>
        <label className="search-field">
          <Search size={16} />
          <input
            aria-label="Search dreams"
            placeholder="Find a detail, a person, a place…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>
      {filtered.length ? (
        <div className="dream-list">
          {filtered.map((dream, i) => (
            <button
              className="dream-row"
              onClick={() => onOpen(dream.id)}
              key={dream.id}
            >
              <span className="entry-number">
                {String(filtered.length - i).padStart(2, "0")}
              </span>
              <div>
                <div className="entry-date">
                  {dateLabel(dream.dreamed_on)}{" "}
                  {dream.audio_id && <Mic size={12} />}
                </div>
                <p>{dream.text || "A voice note waiting to be transcribed."}</p>
                {dream.context && <small>{dream.context}</small>}
              </div>
              <ArrowUpRight size={20} />
            </button>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Moon size={35} />
          <h2>{query ? "No dreams found." : "Make room for the night."}</h2>
          <p>
            {query
              ? "Try a different word or detail."
              : "Your saved dreams will gather here. Start with whatever you remember."}
          </p>
          {!query && (
            <button className="secondary" onClick={onCapture}>
              Capture your first dream
            </button>
          )}
        </div>
      )}
    </section>
  );
}
