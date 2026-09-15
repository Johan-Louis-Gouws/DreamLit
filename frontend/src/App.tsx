import { useEffect, useState } from "react";
import {
  Feather,
  BookOpen,
  Orbit,
  SlidersHorizontal,
  MoonStar,
  ArrowUpRight,
  Globe,
  Search,
  CalendarCheck,
} from "lucide-react";
import { api } from "./api";
import type { Dream, Preferences } from "./types";
import { CaptureView } from "./features/capture/CaptureView";
import { DiaryView } from "./features/diary/DiaryView";
import { DreamDetail } from "./features/diary/DreamDetail";
import { ConnectionsView } from "./features/connections/ConnectionsView";
import { ReflectionPanel } from "./features/reflection/ReflectionPanel";
import { ProviderSettings } from "./features/settings/ProviderSettings";
import { YourWorld } from "./features/insights/YourWorld";
import { Explore } from "./features/insights/Explore";
import { Review } from "./features/insights/Review";
import "./features/insights/insights.css";

export default function App() {
  const [view, setView] = useState("capture"),
    [dreams, setDreams] = useState<Dream[]>([]),
    [selected, setSelected] = useState<string | null>(null),
    [pattern, setPattern] = useState<string | null>(null),
    [refresh, setRefresh] = useState(0),
    [error, setError] = useState("");
  const [preferences, setPreferences] = useState<Preferences>({
    provider: "codex",
    codex_model: "",
    claude_model: "",
    whisper_binary: "",
    whisper_model: "",
    ffmpeg_binary: "ffmpeg",
  });
  useEffect(() => {
    api<Dream[]>("/dreams")
      .then(setDreams)
      .catch(() =>
        setError(
          "The local journal could not be reached. Check that the server is running.",
        ),
      );
  }, [refresh]);
  useEffect(() => {
    api<Preferences>("/settings")
      .then(setPreferences)
      .catch(() => {});
  }, []);
  const changed = () => setRefresh((n) => n + 1);
  const openDream = (id: string) => {
    setPattern(null);
    setSelected(id);
  };
  const openPattern = (id: string) => {
    setSelected(null);
    setPattern(id);
  };
  const nav = [
    { id: "capture", name: "Capture", icon: Feather },
    { id: "diary", name: "Diary", icon: BookOpen },
    { id: "connections", name: "Connections", icon: Orbit },
    { id: "world", name: "Your World", icon: Globe },
    { id: "explore", name: "Explore", icon: Search },
    { id: "review", name: "Review", icon: CalendarCheck },
  ];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button
          className="brand"
          onClick={() => setView("capture")}
          aria-label="DreamLit home"
        >
          <span className="brand-symbol">✦</span>
          <span>
            dreamlit<span className="brand-period">.</span>
          </span>
        </button>
        <span className="brand-subtitle">FIND THE THREAD</span>
        <nav aria-label="Main navigation">
          {nav.map(({ id, name, icon: Icon }) => (
            <button
              key={id}
              aria-label={name}
              aria-current={view === id ? "page" : undefined}
              className={view === id ? "active" : ""}
              onClick={() => setView(id)}
            >
              <Icon size={18} />
              <span>{name}</span>
              {id === "diary" && dreams.length > 0 && (
                <small>{dreams.length}</small>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="tiny-star">✧</span>
          <p>
            Some stories only
            <br />
            make sense together.
          </p>
          <div className="note-rule" />
        </div>
        <div className="sidebar-bottom">
          <button
            className={view === "settings" ? "active" : ""}
            onClick={() => setView("settings")}
          >
            <SlidersHorizontal size={17} />
            <span>Settings</span>
          </button>
          <div className="local-badge">
            <span /> PERSONAL JOURNAL
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span>
            {view === "capture"
              ? "A moment to remember"
              : view === "diary"
                ? "The stories you brought back"
                : view === "connections"
                  ? "Your inner landscape"
                  : view === "world"
                    ? "Your words beside your dreams"
                    : view === "explore"
                      ? "Follow what changes"
                      : view === "review"
                        ? "A gentle look back"
                        : "Your space, your way"}
          </span>
          <button onClick={() => setView("settings")}>
            <span className="online-dot" />
            {preferences.provider === "codex" ? "Codex" : "Claude"} CLI{" "}
            <ArrowUpRight size={12} />
          </button>
        </header>
        <div className="main-content">
          {error && (
            <div role="alert" className="error-message">
              {error}
            </div>
          )}
          {view === "capture" && (
            <CaptureView
              count={dreams.length}
              onSaved={() => changed()}
              onOpen={openDream}
            />
          )}
          {view === "diary" && (
            <DiaryView
              dreams={dreams}
              onOpen={openDream}
              onCapture={() => setView("capture")}
            />
          )}
          {view === "connections" && (
            <ConnectionsView
              provider={preferences.provider}
              onDream={openDream}
              onPattern={openPattern}
              refresh={refresh}
            />
          )}
          {view === "world" && (
            <YourWorld
              key={refresh}
              provider={preferences.provider}
              dreams={dreams}
              onDream={openDream}
            />
          )}
          {view === "explore" && (
            <Explore
              key={refresh}
              provider={preferences.provider}
              dreams={dreams}
              onDream={openDream}
            />
          )}
          {view === "review" && (
            <Review key={refresh} provider={preferences.provider} onDream={openDream} />
          )}
          {view === "settings" && (
            <ProviderSettings
              preferences={preferences}
              onSaved={setPreferences}
            />
          )}
        </div>
      </main>
      {selected && (
        <DreamDetail
          key={selected}
          id={selected}
          provider={preferences.provider}
          onClose={() => setSelected(null)}
          onChange={changed}
          onPattern={openPattern}
        />
      )}
      {pattern && (
        <ReflectionPanel
          key={pattern}
          id={pattern}
          provider={preferences.provider}
          onClose={() => setPattern(null)}
          onDream={openDream}
        />
      )}
    </div>
  );
}
