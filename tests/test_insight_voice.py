import io
import wave

from test_api import client as client
from test_api import finish


def recording():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 1600)
    return buffer.getvalue()


def test_context_voice_saves_original_without_creating_a_dream_or_answer(client):
    response = client.post(
        "/api/insights/voice", files={"file": ("answer.wav", recording(), "audio/wav")}
    )
    assert response.status_code == 201, response.text
    note = response.json()
    assert client.get("/api/audio/" + note["audio_id"]).content == recording()
    assert client.get("/api/dreams").json() == []
    assert client.get("/api/insights/records?kind=answer").json() == []
    assert note["text"] == ""


def test_failed_local_transcription_keeps_audio_and_no_answer(client):
    note = client.post(
        "/api/insights/voice", files={"file": ("answer.wav", recording(), "audio/wav")}
    ).json()
    # Deliberately missing local tool; original audio and manual answer stay usable.
    result = client.post("/api/insights/voice/" + note["id"] + "/transcribe")
    assert result.status_code == 202
    done = finish(client, result.json()["id"])
    assert done["state"] == "failed"
    assert done["error_code"] == "transcription_setup"
    assert client.get("/api/audio/" + note["audio_id"]).status_code == 200
    assert client.get("/api/insights/records").json() == []


def test_context_transcript_requires_user_to_save_the_reviewed_answer(client, monkeypatch):
    from dreamlit.insights import voice

    async def transcript(store, audio_id, job_id, job_dir):
        return "I am enjoying learning something new."

    monkeypatch.setattr(voice, "transcribe_recording", transcript)
    note = client.post(
        "/api/insights/voice", files={"file": ("answer.wav", recording(), "audio/wav")}
    ).json()
    job = client.post("/api/insights/voice/" + note["id"] + "/transcribe").json()
    assert finish(client, job["id"])["state"] == "completed"
    saved = client.get("/api/insights/voice/" + note["id"]).json()
    assert saved["text"] == "I am enjoying learning something new."
    assert client.get("/api/insights/records?kind=answer").json() == []
    answer = client.post(
        "/api/insights/records",
        json={
            "kind": "answer",
            "data": {
                "question": "What are you enjoying?",
                "answer": "I enjoy learning to draw.",
                "audio_id": note["audio_id"],
            },
        },
    )
    assert answer.status_code == 201
    assert answer.json()["data"]["answer"] == "I enjoy learning to draw."
    assert client.get("/api/audio/" + note["audio_id"]).status_code == 200


def test_empty_voice_upload_rejected_without_orphan_audio(client):
    response = client.post("/api/insights/voice", files={"file": ("empty.wav", b"", "audio/wav")})
    assert response.status_code == 422
    with client.app.state.store.connect() as db:
        assert db.execute("SELECT count(*) FROM audio").fetchone()[0] == 0
