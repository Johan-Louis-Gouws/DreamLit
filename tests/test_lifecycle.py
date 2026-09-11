import io
import json
import zipfile

from test_api import client as client
from test_api import finish, save


def test_deletion_removes_derived_evidence_and_export_contains_originals(client):
    one = save(client, "The phone would not dial.")
    save(client, "Nobody heard me at dinner.")
    job = client.post(f"/api/dreams/{one['id']}/analyse", json={"provider": "claude"}).json()
    assert finish(client, job["id"])["state"] == "completed"
    response = client.post("/api/export", json={"include_audio": False})
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        data = json.loads(archive.read("journal.json"))
        assert len(data["dreams"]) == 2
        assert any(r["text"] == "The phone would not dial." for r in data["revisions"])
    assert client.delete(f"/api/dreams/{one['id']}?delete_audio=true").status_code == 200
    assert client.get("/api/dreams/" + one["id"]).status_code == 404
    assert not any(n["kind"] == "theme" for n in client.get("/api/graph").json()["nodes"])


def test_feedback_keeps_what_was_rejected_and_deletion_removes_reflection_jobs(client):
    one = save(client, "The phone would not dial.")
    save(client, "Nobody heard me at dinner.")
    job = client.post(f"/api/dreams/{one['id']}/analyse", json={"provider": "codex"}).json()
    finish(client, job["id"])
    pattern = next(n for n in client.get("/api/graph").json()["nodes"] if n["kind"] == "theme")[
        "pattern_id"
    ]
    client.post(
        f"/api/patterns/{pattern}/feedback",
        json={"verdict": "does_not_fit", "note": "It was just a bad phone."},
    )
    assert client.app.state.store.list_feedback()[0]["pattern_title"] == "Trying to communicate"
    reflection = client.post(
        f"/api/patterns/{pattern}/reflect",
        json={"provider": "claude", "message": "A private correction"},
    ).json()
    assert finish(client, reflection["id"])["state"] == "completed"
    client.delete("/api/dreams/" + one["id"])
    assert client.get("/api/jobs/" + reflection["id"]).status_code == 404
