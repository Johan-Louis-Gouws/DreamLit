CREATE TABLE IF NOT EXISTS insight_records (
 id TEXT PRIMARY KEY,
 kind TEXT NOT NULL CHECK(kind IN ('answer','person','investigation','experiment')),
 current_revision INTEGER NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS insight_record_revisions (
 record_id TEXT NOT NULL REFERENCES insight_records(id) ON DELETE CASCADE,
 revision INTEGER NOT NULL,
 data TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 PRIMARY KEY(record_id, revision)
);
CREATE TABLE IF NOT EXISTS insight_runs (
 id TEXT PRIMARY KEY,
 kind TEXT NOT NULL CHECK(kind IN ('question','turning_points','investigation','portrait','weekly')),
 subject_id TEXT,
 provider TEXT NOT NULL,
 model TEXT,
 output TEXT NOT NULL,
 sources TEXT NOT NULL,
 scope TEXT NOT NULL,
 stale INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS insight_run_sources (
 run_id TEXT NOT NULL REFERENCES insight_runs(id) ON DELETE CASCADE,
 source_kind TEXT NOT NULL,
 source_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 source TEXT NOT NULL,
 PRIMARY KEY(run_id, source_kind, source_id)
);
CREATE INDEX IF NOT EXISTS insight_run_source_lookup
 ON insight_run_sources(source_kind, source_id);
CREATE TABLE IF NOT EXISTS analysis_personal_sources (
 analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
 source_kind TEXT NOT NULL,
 source_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 label TEXT NOT NULL,
 PRIMARY KEY(analysis_id, source_kind, source_id)
);
CREATE INDEX IF NOT EXISTS analysis_personal_source_lookup
 ON analysis_personal_sources(source_kind, source_id);
CREATE TABLE IF NOT EXISTS reflection_personal_sources (
 reflection_id TEXT NOT NULL REFERENCES reflections(id) ON DELETE CASCADE,
 source_kind TEXT NOT NULL,
 source_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 label TEXT NOT NULL,
 PRIMARY KEY(reflection_id, source_kind, source_id)
);
CREATE INDEX IF NOT EXISTS reflection_personal_source_lookup
 ON reflection_personal_sources(source_kind, source_id);
