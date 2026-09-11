"""Offline speech integration; skipped on machines without optional voice setup."""

import time

import pytest
from dreamlit.api import create_app
from dreamlit.config import ROOT, Settings
from fastapi.testclient import TestClient


def test_original_audio_to_reviewed_transcript(tmp_path):
    voice = ROOT / ".dreamlit" / "voice"
    binaries = list(voice.glob("whisper.cpp-*/build/bin/whisper-cli"))
    if not binaries or not (voice / "ggml-base.en.bin").is_file():
        pytest.skip("Run scripts/setup_voice.py to enable the real local speech test")
    source = binaries[0].parents[2] / "samples" / "jfk.wav"
    app = create_app(Settings(data_dir=tmp_path))
    prefs = app.state.store.preferences()
    prefs.whisper_binary = str(binaries[0])
    prefs.whisper_model = str(voice / "ggml-base.en.bin")
    app.state.store.save_preferences(prefs)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        audio = source.read_bytes()
        dream = client.post(
            "/api/audio",
            files={"file": ("sample.wav", audio, "audio/wav")},
            data={"dreamed_on": "2026-09-09"},
        ).json()
        job = client.post(f"/api/dreams/{dream['id']}/transcribe").json()
        for _ in range(300):
            result = client.get("/api/jobs/" + job["id"]).json()
            if result["state"] in ("completed", "failed"):
                break
            time.sleep(0.2)
        assert result["state"] == "completed", result
        transcript = client.get("/api/transcripts/" + result["result_id"]).json()
        assert "country" in transcript["text"].lower()
        assert client.get("/api/dreams/" + dream["id"]).json()["text"] == ""
        accepted = client.post(
            f"/api/dreams/{dream['id']}/accept-transcript",
            json={"transcript_id": transcript["id"], "text": transcript["text"] + " Corrected."},
        )
        assert accepted.status_code == 200
        assert accepted.json()["revision"] == 2
        assert client.get(f"/api/dreams/{dream['id']}/revisions/1").json()["text"] == ""
        assert client.get("/api/audio/" + dream["audio_id"]).content == audio
