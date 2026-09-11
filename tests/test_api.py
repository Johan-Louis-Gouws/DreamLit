import time

import pytest
from dreamlit.api import create_app
from dreamlit.config import Settings
from dreamlit.providers.base import ProviderError, ProviderResponse
from fastapi.testclient import TestClient


class FixtureProvider:
    async def preflight(self):
        return {"installed": True, "version": "Browser test fixture", "status": "ready"}

    async def run(self, request, job_dir):
        if request.task.startswith("insight_"):
            from insight_fixture import response

            return response(request)
        if request.task == "check":
            return ProviderResponse(
                {"summary": "Ready", "observations": [], "patterns": []}, "fixture"
            )
        if request.task == "group":
            return ProviderResponse(
                {"groups": [[item["dream_id"] for item in request.payload["index"]][:3]]}, "fixture"
            )
        dreams = request.payload["dreams"]
        refs = [
            dict(dream_id=d["id"], revision=d["revision"], field="text", quote=d["text"])
            for d in dreams
        ]
        if request.task == "reflect":
            return ProviderResponse(
                {
                    "response": "Where does this situation show up while awake?",
                    "evidence": refs[:1],
                },
                "fixture",
            )
        patterns = []
        if request.task != "extract" and len(refs) >= 2:
            patterns = [
                dict(
                    key="communication",
                    title="Trying to communicate",
                    observation="Communication fails in both entries.",
                    hypothesis=None,
                    question="Does this happen awake?",
                    alternatives=[],
                    counterevidence=refs[2:3],
                    evidence=refs[:2],
                )
            ]
        return ProviderResponse(
            {
                "summary": "A communication difficulty.",
                "observations": [],
                "patterns": patterns,
            },
            "fixture",
        )


class FailingProvider:
    async def run(self, request, job_dir):
        raise ProviderError("usage_limit", "Limit reached")


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    app.state.providers = {"codex": FixtureProvider(), "claude": FixtureProvider()}
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client


def save(client, text):
    response = client.post(
        "/api/dreams", json={"dreamed_on": "2026-09-09", "text": text, "context": ""}
    )
    assert response.status_code == 201
    return response.json()


def finish(client, job_id):
    for _ in range(200):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] in ("completed", "failed", "cancelled"):
            return job
        time.sleep(0.01)
    pytest.fail("job failed to finish")


def test_text_to_connection_and_source_invalidation(client):
    older = save(client, "Nobody heard me at dinner.")
    current = save(client, "The phone would not dial.")
    job = client.post(f"/api/dreams/{current['id']}/analyse", json={"provider": "codex"}).json()
    done = finish(client, job["id"])
    assert done["state"] == "completed", done
    graph = client.get("/api/graph").json()
    assert any(n["label"] == "Trying to communicate" for n in graph["nodes"])
    revised = client.put(
        f"/api/dreams/{older['id']}",
        json={
            "expected_revision": 1,
            "dreamed_on": "2026-09-09",
            "text": "I enjoyed dinner.",
            "context": "",
        },
    )
    assert revised.status_code == 200
    assert not any(n["kind"] == "theme" for n in client.get("/api/graph").json()["nodes"])


def test_failure_does_not_lose_entry_or_fallback(client):
    dream = save(client, "I missed the boat.")
    client.app.state.providers["codex"] = FailingProvider()
    job = client.post(f"/api/dreams/{dream['id']}/analyse", json={"provider": "codex"}).json()
    done = finish(client, job["id"])
    assert done["state"] == "failed"
    assert done["error_code"] == "usage_limit"
    assert client.get(f"/api/dreams/{dream['id']}").json()["text"] == "I missed the boat."
    assert client.get(f"/api/dreams/{dream['id']}/analyses").json() == []


def test_counterexamples_are_available_for_reflection_but_not_graph_recurrences(client):
    for text in ["The phone worked.", "Nobody heard me at dinner.", "The phone would not dial."]:
        current = save(client, text)
    job = client.post(f"/api/dreams/{current['id']}/analyse", json={"provider": "codex"}).json()
    assert finish(client, job["id"])["state"] == "completed"
    graph = client.get("/api/graph").json()
    pattern_id = next(n["pattern_id"] for n in graph["nodes"] if n["kind"] == "theme")
    pattern = client.get(f"/api/patterns/{pattern_id}").json()
    counterexample = pattern["counterevidence"][0]["dream_id"]
    assert counterexample not in {e["source"] for e in graph["edges"]}
    seen = []
    provider = client.app.state.providers["codex"]
    run = provider.run

    async def observed(request, directory):
        seen.extend(d["id"] for d in request.payload["dreams"])
        return await run(request, directory)

    provider.run = observed
    reply = client.post(
        f"/api/patterns/{pattern_id}/reflect",
        json={"provider": "codex", "message": "What about the dream where it worked?"},
    ).json()
    assert finish(client, reply["id"])["state"] == "completed"
    assert counterexample in seen


def test_foreign_origin_and_stale_update_rejected(client):
    assert (
        client.post(
            "/api/dreams", headers={"origin": "https://attacker.invalid"}, json={}
        ).status_code
        == 403
    )
    dream = save(client, "First version")
    update = {
        "expected_revision": 1,
        "dreamed_on": "2026-09-09",
        "text": "Second version",
        "context": "",
    }
    assert client.put(f"/api/dreams/{dream['id']}", json=update).status_code == 200
    assert client.put(f"/api/dreams/{dream['id']}", json=update).status_code == 409
