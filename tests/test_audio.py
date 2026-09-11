from dreamlit.api import create_app
from dreamlit.config import Settings
from fastapi.testclient import TestClient


def test_recording_survives_missing_transcription_tool(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path)), base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/audio",
            files={"file": ("dream.wav", b"fake audio persistence fixture", "audio/wav")},
            data={"dreamed_on": "2026-09-09"},
        )
        assert response.status_code == 201
        dream = response.json()
        assert dream["audio_id"]
        assert (
            client.get("/api/audio/" + dream["audio_id"]).content
            == b"fake audio persistence fixture"
        )
        assert (
            client.post(
                "/api/dreams/" + dream["id"] + "/analyse", json={"provider": "codex"}
            ).status_code
            == 422
        )


def test_audio_filename_cannot_escape_storage(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path)), base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/audio",
            files={"file": ("../../escape.wav", b"bytes", "audio/wav")},
            data={"dreamed_on": "2026-09-09"},
        )
        assert response.status_code == 201
        assert not (tmp_path.parent / "escape.wav").exists()


def test_invalid_transcript_edit_is_a_validation_error(tmp_path):
    from dreamlit.storage import now

    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        dream = client.post(
            "/api/audio",
            files={"file": ("voice.wav", b"voice", "audio/wav")},
            data={"dreamed_on": "2026-09-09"},
        ).json()
        with app.state.store.connect() as db:
            db.execute(
                "INSERT INTO transcripts VALUES (?,?,?,?,?)",
                ("proposal", dream["id"], 1, "Words", now()),
            )
        response = client.post(
            f"/api/dreams/{dream['id']}/accept-transcript",
            json={"transcript_id": "proposal", "text": "   "},
        )
        assert response.status_code == 422
        assert client.get("/api/dreams/" + dream["id"]).json()["revision"] == 1


def test_reopening_an_audio_entry_recovers_a_pending_transcript(tmp_path):
    from dreamlit.storage import now

    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        dream = client.post(
            "/api/audio",
            files={"file": ("voice.wav", b"voice", "audio/wav")},
            data={"dreamed_on": "2026-09-09"},
        ).json()
        with app.state.store.connect() as db:
            db.execute(
                "INSERT INTO transcripts VALUES (?,?,?,?,?)",
                ("pending", dream["id"], 1, "A proposed transcript", now()),
            )
        response = client.get(f"/api/dreams/{dream['id']}/activity")
        assert response.status_code == 200
        assert response.json()["transcript"]["text"] == "A proposed transcript"
