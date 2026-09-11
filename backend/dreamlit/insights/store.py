import json

from ..storage import Conflict, now, uid
from .records import RECORD_MODELS, validate_record_data


class InsightStore:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _decode_record(row):
        item = dict(row)
        item["data"] = json.loads(item["data"])
        return item

    @staticmethod
    def _current_record(db, record_id):
        return db.execute(
            """SELECT r.id,r.kind,r.current_revision AS revision,v.data,
               r.created_at,v.updated_at
               FROM insight_records r JOIN insight_record_revisions v
               ON v.record_id=r.id AND v.revision=r.current_revision
               WHERE r.id=?""",
            (record_id,),
        ).fetchone()

    @staticmethod
    def _require_kind(db, record_id, kind):
        row = InsightStore._current_record(db, record_id)
        if row is None or row["kind"] != kind:
            raise ValueError(f"Linked {kind} record was not found.")
        return row

    @staticmethod
    def _require_dream(db, dream_id):
        if not db.execute("SELECT 1 FROM dreams WHERE id=?", (dream_id,)).fetchone():
            raise ValueError("Linked dream was not found.")

    @staticmethod
    def _validate_links(db, kind, data):
        if kind == "answer":
            if data["person_id"]:
                InsightStore._require_kind(db, data["person_id"], "person")
            if data["dream_id"]:
                InsightStore._require_dream(db, data["dream_id"])
            if data["audio_id"] and not db.execute(
                "SELECT 1 FROM audio WHERE id=?", (data["audio_id"],)
            ).fetchone():
                raise ValueError("Linked audio recording was not found.")
        elif kind == "investigation":
            for dream_id in data["dream_ids"]:
                InsightStore._require_dream(db, dream_id)
        elif kind == "experiment":
            if data["person_id"]:
                InsightStore._require_kind(db, data["person_id"], "person")
            if data["investigation_id"]:
                InsightStore._require_kind(db, data["investigation_id"], "investigation")

    @staticmethod
    def _invalidate(db, kind, record_id):
        db.execute(
            """UPDATE insight_runs SET stale=1 WHERE id IN
               (SELECT run_id FROM insight_run_sources
                WHERE source_kind=? AND source_id=?)""",
            (kind, record_id),
        )
        db.execute(
            """UPDATE analyses SET stale=1 WHERE id IN
               (SELECT analysis_id FROM analysis_personal_sources
                WHERE source_kind=? AND source_id=?)""",
            (kind, record_id),
        )
        db.execute(
            """UPDATE reflections SET stale=1 WHERE id IN
               (SELECT reflection_id FROM reflection_personal_sources
                WHERE source_kind=? AND source_id=?)""",
            (kind, record_id),
        )

    @staticmethod
    def _insert_revision(db, row, data):
        revision = row["revision"] + 1
        updated_at = now()
        db.execute(
            "INSERT INTO insight_record_revisions VALUES (?,?,?,?)",
            (row["id"], revision, json.dumps(data, sort_keys=True), updated_at),
        )
        db.execute(
            "UPDATE insight_records SET current_revision=? WHERE id=?",
            (revision, row["id"]),
        )
        InsightStore._invalidate(db, row["kind"], row["id"])

    def create_record(self, kind, data):
        validated = validate_record_data(kind, data)
        record_id, created_at = uid(), now()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._validate_links(db, kind, validated)
            db.execute(
                "INSERT INTO insight_records VALUES (?,?,1,?)",
                (record_id, kind, created_at),
            )
            db.execute(
                "INSERT INTO insight_record_revisions VALUES (?,1,?,?)",
                (record_id, json.dumps(validated, sort_keys=True), created_at),
            )
        return self.get_record(record_id)

    def get_record(self, record_id):
        with self.store.connect() as db:
            row = self._current_record(db, record_id)
        if row is None:
            raise KeyError("Insight record not found")
        return self._decode_record(row)

    def list_records(self, kind=None):
        if kind is not None and kind not in RECORD_MODELS:
            raise ValueError("Unknown insight record kind.")
        with self.store.connect() as db:
            rows = db.execute(
                """SELECT r.id,r.kind,r.current_revision AS revision,v.data,
                   r.created_at,v.updated_at
                   FROM insight_records r JOIN insight_record_revisions v
                   ON v.record_id=r.id AND v.revision=r.current_revision
                   WHERE (? IS NULL OR r.kind=?) ORDER BY v.updated_at DESC""",
                (kind, kind),
            ).fetchall()
        return [self._decode_record(row) for row in rows]

    def update_record(self, record_id, expected_revision, data):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._current_record(db, record_id)
            if row is None:
                raise KeyError("Insight record not found")
            if row["revision"] != expected_revision:
                raise Conflict("This record changed. Reload it before saving.")
            validated = validate_record_data(row["kind"], data)
            self._validate_links(db, row["kind"], validated)
            self._insert_revision(db, row, validated)
        return self.get_record(record_id)

    def delete_record(self, record_id):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            target = self._current_record(db, record_id)
            if target is None:
                raise KeyError("Insight record not found")

            for row in db.execute(
                """SELECT r.id,r.kind,r.current_revision AS revision,v.data
                   FROM insight_records r JOIN insight_record_revisions v
                   ON v.record_id=r.id AND v.revision=r.current_revision
                   WHERE r.id<>?""",
                (record_id,),
            ).fetchall():
                data = json.loads(row["data"])
                changed = False
                if target["kind"] == "person" and row["kind"] in ("answer", "experiment"):
                    if data.get("person_id") == record_id:
                        data["person_id"] = None
                        changed = True
                if target["kind"] == "investigation" and row["kind"] == "experiment":
                    if data.get("investigation_id") == record_id:
                        data["investigation_id"] = None
                        changed = True
                if changed:
                    self._insert_revision(db, row, data)

            db.execute(
                """DELETE FROM insight_runs WHERE subject_id=? OR id IN
                   (SELECT run_id FROM insight_run_sources
                    WHERE source_kind=? AND source_id=?)""",
                (record_id, target["kind"], record_id),
            )
            db.execute(
                """DELETE FROM analyses WHERE id IN
                   (SELECT analysis_id FROM analysis_personal_sources
                    WHERE source_kind=? AND source_id=?)""",
                (target["kind"], record_id),
            )
            db.execute(
                """DELETE FROM reflections WHERE id IN
                   (SELECT reflection_id FROM reflection_personal_sources
                    WHERE source_kind=? AND source_id=?)""",
                (target["kind"], record_id),
            )
            db.execute("DELETE FROM insight_records WHERE id=?", (record_id,))
        return {"deleted": True}

    def record_history(self, record_id):
        with self.store.connect() as db:
            record = db.execute(
                "SELECT id,kind,created_at FROM insight_records WHERE id=?", (record_id,)
            ).fetchone()
            if record is None:
                raise KeyError("Insight record not found")
            rows = db.execute(
                """SELECT ? AS id,? AS kind,revision,data,? AS created_at,updated_at
                   FROM insight_record_revisions WHERE record_id=? ORDER BY revision DESC""",
                (record["id"], record["kind"], record["created_at"], record_id),
            ).fetchall()
        return [self._decode_record(row) for row in rows]

    @staticmethod
    def _source_for(record):
        data = record["data"]
        fields = {}
        for key, value in data.items():
            if value is None or isinstance(value, bool):
                continue
            if isinstance(value, list):
                value = "\n".join(str(item) for item in value)
            else:
                value = str(value)
            if value:
                fields[key] = value
        label_key = {
            "answer": "question",
            "person": "name",
            "investigation": "question",
            "experiment": "action",
        }[record["kind"]]
        return {
            "kind": record["kind"],
            "id": record["id"],
            "revision": record["revision"],
            "date": record["updated_at"][:10],
            "label": data[label_key],
            "fields": fields,
        }

    def sources(self):
        records = self.list_records()
        excluded_people = {
            item["id"]
            for item in records
            if item["kind"] == "person" and not item["data"]["include_in_analysis"]
        }
        eligible = []
        for item in records:
            data = item["data"]
            if item["kind"] == "answer" and (
                data["status"] != "current" or data.get("person_id") in excluded_people
            ):
                continue
            if item["kind"] == "person" and not data["include_in_analysis"]:
                continue
            eligible.append(self._source_for(item))
        return eligible

    @staticmethod
    def _actual_source(db, source):
        kind, source_id = source.get("kind"), source.get("id")
        if kind == "dream":
            row = db.execute(
                """SELECT d.current_revision AS revision,r.dreamed_on,r.text,r.context
                   FROM dreams d JOIN dream_revisions r
                   ON r.dream_id=d.id AND r.revision=d.current_revision WHERE d.id=?""",
                (source_id,),
            ).fetchone()
            if row is None:
                raise Conflict("A source dream was deleted during generation.")
            if row["revision"] != source.get("revision"):
                raise Conflict("A source dream changed during generation.")
            fields = {"text": row["text"], "context": row["context"]}
            if source.get("date") != row["dreamed_on"] or source.get("fields") != fields:
                raise ValueError("Dream source metadata does not match the selected revision.")
            return fields
        if kind not in RECORD_MODELS:
            raise ValueError("Unknown insight source kind.")
        row = InsightStore._current_record(db, source_id)
        if row is None:
            raise Conflict("A personal source was deleted during generation.")
        if row["kind"] != kind or row["revision"] != source.get("revision"):
            raise Conflict("A personal source changed during generation.")
        actual = InsightStore._source_for(InsightStore._decode_record(row))
        if source.get("date") != actual["date"] or source.get("fields") != actual["fields"]:
            raise ValueError("Personal source metadata does not match the selected revision.")
        return actual["fields"]

    @staticmethod
    def _validate_output(kind, output, actual_sources):
        if not isinstance(output, dict) or not isinstance(output.get("sections"), list):
            raise ValueError("Insight output has an invalid shape.")
        for section in output["sections"]:
            references = section.get("evidence", []) + section.get("counterevidence", [])
            dream_ids = set()
            for reference in references:
                key = (
                    reference.get("source_kind"),
                    reference.get("source_id"),
                    reference.get("revision"),
                )
                fields = actual_sources.get(key)
                if fields is None:
                    raise ValueError("Evidence cites a source that was not selected.")
                field = reference.get("field")
                quote = reference.get("quote")
                if field not in fields or not isinstance(quote, str) or not quote.strip():
                    raise ValueError("Evidence quote has an invalid source field.")
                if quote not in fields[field]:
                    raise ValueError("Evidence quote does not match its selected source.")
                if key[0] == "dream":
                    dream_ids.add(key[1])
            if kind == "turning_points" and len(dream_ids) < 2:
                raise ValueError("Turning point sections require two distinct dream sources.")

    def save_run(self, kind, subject_id, provider, model, output, sources, scope):
        if kind not in ("question", "turning_points", "investigation", "portrait", "weekly"):
            raise ValueError("Unknown insight run kind.")
        run_id = uid()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            actual_sources = {}
            for source in sources:
                key = (source.get("kind"), source.get("id"), source.get("revision"))
                if key in actual_sources:
                    raise ValueError("An insight source was selected more than once.")
                actual_sources[key] = self._actual_source(db, source)
            self._validate_output(kind, output, actual_sources)
            db.execute(
                "INSERT INTO insight_runs VALUES (?,?,?,?,?,?,?,?,0,?)",
                (
                    run_id,
                    kind,
                    subject_id,
                    provider,
                    model,
                    json.dumps(output, sort_keys=True),
                    json.dumps(sources, sort_keys=True),
                    json.dumps(scope, sort_keys=True),
                    now(),
                ),
            )
            for source in sources:
                db.execute(
                    "INSERT INTO insight_run_sources VALUES (?,?,?,?,?)",
                    (
                        run_id,
                        source["kind"],
                        source["id"],
                        source["revision"],
                        json.dumps(source, sort_keys=True),
                    ),
                )
        return self.get_run(run_id)

    @staticmethod
    def _decode_run(row):
        item = dict(row)
        for key in ("output", "sources", "scope"):
            item[key] = json.loads(item[key])
        item["stale"] = bool(item["stale"])
        return item

    def get_run(self, run_id):
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM insight_runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError("Insight run not found")
        return self._decode_run(row)

    def list_runs(self, kind=None, subject_id=None):
        with self.store.connect() as db:
            rows = db.execute(
                """SELECT * FROM insight_runs WHERE (? IS NULL OR kind=?)
                   AND (? IS NULL OR subject_id=?) ORDER BY created_at DESC""",
                (kind, kind, subject_id, subject_id),
            ).fetchall()
        return [self._decode_run(row) for row in rows]

    @staticmethod
    def unlink_dream(db, dream_id):
        rows = db.execute(
            """SELECT r.id,r.kind,r.current_revision AS revision,v.data
               FROM insight_records r JOIN insight_record_revisions v
               ON v.record_id=r.id AND v.revision=r.current_revision
               WHERE r.kind IN ('answer','investigation')"""
        ).fetchall()
        for row in rows:
            data = json.loads(row["data"])
            changed = False
            if row["kind"] == "answer" and data.get("dream_id") == dream_id:
                data["dream_id"] = None
                changed = True
            if row["kind"] == "investigation" and dream_id in data.get("dream_ids", []):
                data["dream_ids"] = [item for item in data["dream_ids"] if item != dream_id]
                changed = True
            if changed:
                InsightStore._insert_revision(db, row, data)
