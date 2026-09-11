import json
import zipfile


def export_journal(store, target, include_audio=False):
    with store.connect() as db:
        db.execute("BEGIN")
        tables = {
            name: [dict(row) for row in db.execute("SELECT * FROM " + table)]
            for name, table in [
                ("dreams", "dreams"),
                ("revisions", "dream_revisions"),
                ("associations", "associations"),
                ("feedback", "feedback"),
                ("analyses", "analyses"),
                ("patterns", "patterns"),
                ("reflections", "reflections"),
                ("audio", "audio"),
                ("insight_records", "insight_records"),
                ("insight_record_revisions", "insight_record_revisions"),
                ("insight_runs", "insight_runs"),
                ("insight_run_sources", "insight_run_sources"),
                ("analysis_personal_sources", "analysis_personal_sources"),
                ("reflection_personal_sources", "reflection_personal_sources"),
                ("insight_voice", "insight_voice"),
            ]
        }
        tables["format_version"] = 1
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("journal.json", json.dumps(tables, ensure_ascii=False, indent=2))
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "version": 1,
                        "journal": "journal.json",
                        "audio_included": include_audio,
                    }
                ),
            )
            if include_audio:
                for row in tables["audio"]:
                    path = store.data_dir / "audio" / row["filename"]
                    if path.is_file():
                        archive.write(path, "audio/" + row["id"])
    return target
