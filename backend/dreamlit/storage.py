import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import Dream, DreamCreate, Preferences


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in ("audio", "jobs", "exports"):
            (self.data_dir / name).mkdir(exist_ok=True, mode=0o700)
        self.path = self.data_dir / "journal.sqlite3"
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise ValueError("This journal was created by a newer DreamLit version.")
            if version == 0:
                schema = Path(__file__).with_name("schema.sql").read_text()
                db.executescript("BEGIN IMMEDIATE;\n" + schema + "\nCOMMIT;")
            insight_schema = Path(__file__).with_name("insights").joinpath("schema.sql").read_text()
            db.executescript(insight_schema)
            voice_schema = Path(__file__).with_name("insights").joinpath("voice.sql").read_text()
            db.executescript(voice_schema)
            reflection_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(reflections)")
            }
            if "stale" not in reflection_columns:
                db.execute("ALTER TABLE reflections ADD COLUMN stale INTEGER NOT NULL DEFAULT 0")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_dream(self, data: DreamCreate) -> Dream:
        return self._create(str(data.dreamed_on), data.text, data.context, None)

    def _create(self, dreamed_on, text, context, audio_id):
        dream_id, created = uid(), now()
        with self.connect() as db:
            db.execute("INSERT INTO dreams VALUES (?,1,?)", (dream_id, created))
            db.execute(
                "INSERT INTO dream_revisions VALUES (?,1,?,?,?,?,?)",
                (dream_id, dreamed_on, text, context, audio_id, created),
            )
        return self.get_dream(dream_id)

    def get_revision(self, dream_id: str, revision: int) -> Dream:
        with self.connect() as db:
            row = db.execute(
                "SELECT dream_id AS id, dreamed_on,text,context,revision,audio_id,created_at FROM dream_revisions WHERE dream_id=? AND revision=?",
                (dream_id, revision),
            ).fetchone()
        if row is None:
            raise KeyError("Dream not found")
        return Dream(**dict(row))

    def get_dream(self, dream_id: str) -> Dream:
        with self.connect() as db:
            row = db.execute(
                "SELECT current_revision FROM dreams WHERE id=?", (dream_id,)
            ).fetchone()
        if row is None:
            raise KeyError("Dream not found")
        return self.get_revision(dream_id, row[0])

    def list_dreams(self, query: str = "") -> list[Dream]:
        with self.connect() as db:
            rows = db.execute(
                """SELECT r.dream_id AS id,r.dreamed_on,r.text,r.context,r.revision,r.audio_id,r.created_at
                FROM dream_revisions r JOIN dreams d ON d.id=r.dream_id AND d.current_revision=r.revision
                WHERE instr(lower(r.text || ' ' || r.context),lower(?))>0 ORDER BY r.dreamed_on DESC,r.created_at DESC""",
                (query,),
            ).fetchall()
        return [Dream(**dict(r)) for r in rows]

    def revise_dream(self, dream_id, expected_revision, data: DreamCreate):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM dream_revisions WHERE dream_id=? AND revision=(SELECT current_revision FROM dreams WHERE id=?)",
                (dream_id, dream_id),
            ).fetchone()
            if row is None:
                raise KeyError("Dream not found")
            if row["revision"] != expected_revision:
                raise Conflict("This dream changed. Reload it before saving.")
            revision = expected_revision + 1
            db.execute(
                "INSERT INTO dream_revisions VALUES (?,?,?,?,?,?,?)",
                (
                    dream_id,
                    revision,
                    str(data.dreamed_on),
                    data.text,
                    data.context,
                    row["audio_id"],
                    now(),
                ),
            )
            db.execute("UPDATE dreams SET current_revision=? WHERE id=?", (revision, dream_id))
            db.execute(
                "UPDATE analyses SET stale=1 WHERE id IN (SELECT analysis_id FROM analysis_sources WHERE dream_id=?)",
                (dream_id,),
            )
            db.execute(
                """UPDATE insight_runs SET stale=1 WHERE id IN
                (SELECT run_id FROM insight_run_sources
                 WHERE source_kind='dream' AND source_id=?)""",
                (dream_id,),
            )
        return self.get_dream(dream_id)

    def preferences(self):
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key='preferences'").fetchone()
        return Preferences.model_validate_json(row[0]) if row else Preferences()

    def save_preferences(self, preferences: Preferences):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO settings VALUES ('preferences',?)",
                (preferences.model_dump_json(),),
            )
        return preferences

    def add_association(self, label, meaning, dream_id=None):
        item = dict(id=uid(), label=label, meaning=meaning, dream_id=dream_id, created_at=now())
        with self.connect() as db:
            db.execute(
                "INSERT INTO associations VALUES (:id,:label,:meaning,:dream_id,:created_at)",
                item,
            )
        return item

    def list_associations(self):
        with self.connect() as db:
            return [
                dict(r) for r in db.execute("SELECT * FROM associations ORDER BY created_at DESC")
            ]

    def add_feedback(self, pattern_id, verdict, note):
        item = dict(
            id=uid(),
            pattern_id=pattern_id,
            verdict=verdict,
            note=note,
            created_at=now(),
        )
        with self.connect() as db:
            db.execute(
                "INSERT INTO feedback VALUES (:id,:pattern_id,:verdict,:note,:created_at)",
                item,
            )
        return item

    def list_feedback(self, pattern_id=None):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    """SELECT f.*, json_extract(p.output,'$.title') AS pattern_title,
                    json_extract(p.output,'$.observation') AS observation,
                    json_extract(p.output,'$.hypothesis') AS hypothesis
                    FROM feedback f JOIN patterns p ON p.id=f.pattern_id
                    WHERE (? IS NULL OR pattern_id=?) ORDER BY f.created_at""",
                    (pattern_id, pattern_id),
                )
            ]

    def create_job(self, kind, payload, provider):
        encoded = json.dumps(payload, sort_keys=True)
        with self.connect() as db:
            existing = db.execute(
                "SELECT id FROM jobs WHERE kind=? AND payload=? AND provider IS ? AND state IN ('queued','running')",
                (kind, encoded, provider),
            ).fetchone()
            if existing:
                return self.get_job(existing[0])
            job_id = uid()
            db.execute(
                "INSERT INTO jobs VALUES (?,?,?,'queued','Waiting',?,NULL,NULL,?)",
                (job_id, kind, provider, encoded, now()),
            )
        return self.get_job(job_id)

    def get_job(self, job_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError("Job not found")
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item

    def set_job(self, job_id, *, state=None, stage=None, error_code=None, result_id=None):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET state=COALESCE(?,state),stage=COALESCE(?,stage),error_code=?,result_id=COALESCE(?,result_id) WHERE id=? AND state NOT IN ('completed','failed','cancelled')",
                (state, stage, error_code, result_id, job_id),
            )

    def recover_jobs(self):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET state='failed',error_code='interrupted',stage='Interrupted; retry available' WHERE state IN ('running','queued')"
            )

    def save_analysis(self, job_id, provider, model, sources, scope, output, personal_context=None):
        from .insights.store import InsightStore

        analysis_id = uid()
        revisions = {d.id: d.revision for d in sources}
        personal_context = personal_context or []
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            stale = False
            for dream_id, revision in revisions.items():
                row = db.execute(
                    "SELECT current_revision FROM dreams WHERE id=?", (dream_id,)
                ).fetchone()
                if row is None:
                    raise Conflict("A source dream was deleted during analysis.")
                stale |= row[0] != revision
            for source in personal_context:
                InsightStore.require_eligible_source(db, source)
                row = db.execute(
                    "SELECT kind,current_revision FROM insight_records WHERE id=?",
                    (source["id"],),
                ).fetchone()
                if row is None:
                    raise Conflict("A personal source was deleted during analysis.")
                if row["kind"] != source["kind"]:
                    raise Conflict("A personal source changed during analysis.")
                stale |= row["current_revision"] != source["revision"]
            db.execute(
                "INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    analysis_id,
                    job_id,
                    provider,
                    model,
                    json.dumps(revisions),
                    scope.model_dump_json(),
                    output.model_dump_json(),
                    int(stale),
                    now(),
                ),
            )
            for dream_id, revision in revisions.items():
                db.execute(
                    "INSERT INTO analysis_sources VALUES (?,?,?)",
                    (analysis_id, dream_id, revision),
                )
            for source in personal_context:
                db.execute(
                    "INSERT INTO analysis_personal_sources VALUES (?,?,?,?,?)",
                    (
                        analysis_id,
                        source["kind"],
                        source["id"],
                        source["revision"],
                        source["label"],
                    ),
                )
            for pattern in output.patterns:
                db.execute(
                    "INSERT INTO patterns VALUES (?,?,?)",
                    (uid(), analysis_id, pattern.model_dump_json()),
                )
        return self.get_analysis(analysis_id)

    @staticmethod
    def decode_analysis(row):
        item = dict(row)
        for key in ("source_revisions", "scope", "output"):
            item[key] = json.loads(item[key])
        item["stale"] = bool(item["stale"])
        return item

    def get_analysis(self, analysis_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
            if row is None:
                raise KeyError("Analysis not found")
            item = self.decode_analysis(row)
            item["patterns"] = [
                {**json.loads(r["output"]), "id": r["id"], "analysis_id": analysis_id}
                for r in db.execute("SELECT * FROM patterns WHERE analysis_id=?", (analysis_id,))
            ]
            item["personal_context_sources"] = [
                {
                    "kind": row["source_kind"],
                    "id": row["source_id"],
                    "revision": row["revision"],
                    "label": row["label"],
                }
                for row in db.execute(
                    """SELECT source_kind,source_id,revision,label
                    FROM analysis_personal_sources WHERE analysis_id=?
                    ORDER BY source_kind,source_id""",
                    (analysis_id,),
                )
            ]
        return item

    def list_analyses(self, dream_id=None):
        with self.connect() as db:
            rows = db.execute(
                "SELECT DISTINCT a.id FROM analyses a LEFT JOIN analysis_sources s ON s.analysis_id=a.id WHERE (? IS NULL OR s.dream_id=?) ORDER BY a.created_at DESC",
                (dream_id, dream_id),
            ).fetchall()
        return [self.get_analysis(r[0]) for r in rows]

    def get_pattern(self, pattern_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT p.*,a.provider,a.model,a.stale,a.scope FROM patterns p JOIN analyses a ON a.id=p.analysis_id WHERE p.id=?",
                (pattern_id,),
            ).fetchone()
            if row is None:
                raise KeyError("Pattern not found")
            result = {
                **json.loads(row["output"]),
                **{k: row[k] for k in ("id", "analysis_id", "provider", "model", "stale")},
            }
            result["scope"] = json.loads(row["scope"])
            result["reflections"] = []
            for reflection_row in db.execute(
                "SELECT * FROM reflections WHERE pattern_id=? ORDER BY created_at",
                (pattern_id,),
            ):
                reflection = {
                    **dict(reflection_row),
                    "output": json.loads(reflection_row["output"]),
                }
                reflection["stale"] = bool(reflection["stale"])
                reflection["personal_context_sources"] = [
                    {
                        "kind": row["source_kind"],
                        "id": row["source_id"],
                        "revision": row["revision"],
                        "label": row["label"],
                    }
                    for row in db.execute(
                        """SELECT source_kind,source_id,revision,label
                        FROM reflection_personal_sources WHERE reflection_id=?
                        ORDER BY source_kind,source_id""",
                        (reflection["id"],),
                    )
                ]
                result["reflections"].append(reflection)
        result["feedback"] = self.list_feedback(pattern_id)
        return result

    def save_reflection(self, pattern_id, provider, message, output, personal_context=None):
        from .insights.store import InsightStore

        reflection_id = uid()
        personal_context = personal_context or []
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            stale = False
            for source in personal_context:
                InsightStore.require_eligible_source(db, source)
                row = db.execute(
                    "SELECT kind,current_revision FROM insight_records WHERE id=?",
                    (source["id"],),
                ).fetchone()
                if row is None:
                    raise Conflict("A personal source was deleted during reflection.")
                if row["kind"] != source["kind"]:
                    raise Conflict("A personal source changed during reflection.")
                stale |= row["current_revision"] != source["revision"]
            db.execute(
                """INSERT INTO reflections
                (id,pattern_id,provider,message,output,created_at,stale)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    reflection_id,
                    pattern_id,
                    provider,
                    message,
                    output.model_dump_json(),
                    now(),
                    int(stale),
                ),
            )
            for source in personal_context:
                db.execute(
                    "INSERT INTO reflection_personal_sources VALUES (?,?,?,?,?)",
                    (
                        reflection_id,
                        source["kind"],
                        source["id"],
                        source["revision"],
                        source["label"],
                    ),
                )
        return reflection_id

    def create_audio_dream(self, dreamed_on, audio_id):
        return self._create(dreamed_on, "", "", audio_id)

    def delete_dream(self, dream_id, delete_audio=True):
        dream = self.get_dream(dream_id)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            from .insights.store import InsightStore

            InsightStore.unlink_dream(db, dream_id)
            db.execute(
                """DELETE FROM insight_runs WHERE id IN
                (SELECT run_id FROM insight_run_sources
                 WHERE source_kind='dream' AND source_id=?)""",
                (dream_id,),
            )
            db.execute(
                """DELETE FROM jobs WHERE json_extract(payload,'$.pattern_id') IN
                (SELECT p.id FROM patterns p JOIN analysis_sources s ON s.analysis_id=p.analysis_id WHERE s.dream_id=?)""",
                (dream_id,),
            )
            db.execute(
                "DELETE FROM analyses WHERE id IN (SELECT analysis_id FROM analysis_sources WHERE dream_id=?)",
                (dream_id,),
            )
            # Job snapshots also contain diary data and must be removed on deletion.
            db.execute(
                "DELETE FROM jobs WHERE json_extract(payload,'$.dream_id')=?",
                (dream_id,),
            )
            db.execute("DELETE FROM dreams WHERE id=?", (dream_id,))
            audio = (
                db.execute("SELECT filename FROM audio WHERE id=?", (dream.audio_id,)).fetchone()
                if dream.audio_id
                else None
            )
            if delete_audio and audio:
                db.execute("DELETE FROM audio WHERE id=?", (dream.audio_id,))
        if delete_audio and audio:
            (self.data_dir / "audio" / audio[0]).unlink(missing_ok=True)
