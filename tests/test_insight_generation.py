import json

import pytest
from dreamlit.models import ContextSnapshot
from dreamlit.providers.base import ProviderError
from test_api import client as client
from test_api import finish, save


def record(client, kind, **data):
    response = client.post("/api/insights/records", json={"kind": kind, "data": data})
    assert response.status_code == 201, response.text
    return response.json()


def generate(client, kind, **options):
    response = client.post(
        "/api/insights/runs", json={"kind": kind, "provider": "codex", **options}
    )
    assert response.status_code == 202, response.text
    done = finish(client, response.json()["id"])
    assert done["state"] == "completed", done
    return client.get("/api/insights/runs/" + done["result_id"]).json()


def test_world_context_is_optional_in_old_payloads_and_used_by_dream_analysis(client):
    assert "personal_context" in ContextSnapshot.model_fields
    answer = record(client, "answer", question="What is on your mind?", answer="A new job")
    hidden = record(
        client, "answer", question="Private?", answer="Excluded words", status="excluded"
    )
    dream = save(client, "I arrived at a new office.")
    seen = []
    provider = client.app.state.providers["codex"]
    original = provider.run

    async def capture(request, folder):
        seen.append(request.payload)
        return await original(request, folder)

    provider.run = capture
    job = client.post(f"/api/dreams/{dream['id']}/analyse", json={"provider": "codex"}).json()
    assert finish(client, job["id"])["state"] == "completed"
    assert any(s["id"] == answer["id"] for s in seen[0]["personal_context"])
    assert hidden["id"] not in json.dumps(seen)
    assert "Excluded words" not in json.dumps(seen)
    analyses = client.get(f"/api/dreams/{dream['id']}/analyses").json()
    assert any(s["id"] == answer["id"] for s in analyses[0]["personal_context_sources"])
    client.put(
        "/api/insights/records/" + answer["id"],
        json={
            "expected_revision": 1,
            "data": {**answer["data"], "answer": "The job has settled down"},
        },
    )
    assert client.get("/api/analyses/" + analyses[0]["id"]).json()["stale"]


def test_question_works_without_dreams_and_does_not_save_an_answer(client):
    run = generate(client, "question")
    assert run["output"]["question"].strip()
    assert client.get("/api/insights/records?kind=answer").json() == []


@pytest.mark.parametrize("kind", ["turning_points", "investigation", "portrait", "weekly"])
def test_generated_features_save_sources_and_scope(client, kind):
    person = record(client, "person", name="Maya", aliases=["May"], relationship="A friend")
    inquiry = record(client, "investigation", question="How do I respond when Maya asks for help?")
    for day, text in [
        ("2026-09-08", "Maya asked for help and I went away."),
        ("2026-09-10", "Maya asked for help and I stayed."),
    ]:
        client.post("/api/dreams", json={"dreamed_on": day, "text": text})
    options = {"date_from": "2026-09-05", "date_to": "2026-09-11"}
    if kind == "portrait":
        options["subject_id"] = person["id"]
    elif kind == "investigation":
        options["subject_id"] = inquiry["id"]
    result = generate(client, kind, **options)
    assert result["kind"] == kind
    assert not result["stale"]
    assert result["scope"]["total_eligible_dreams"] == 2
    assert result["sources"]
    assert result["output"]["sections"]
    assert result["output"]["sections"][0]["evidence"]


def test_weekly_letter_respects_requested_dates(client):
    old = client.post(
        "/api/dreams", json={"dreamed_on": "2025-09-05", "text": "A past birthday"}
    ).json()
    recent = client.post(
        "/api/dreams", json={"dreamed_on": "2026-09-10", "text": "I celebrated with friends"}
    ).json()
    result = generate(client, "weekly", date_from="2026-09-05", date_to="2026-09-11")
    assert result["scope"]["included_dream_ids"] == [recent["id"]]
    assert old["id"] not in json.dumps(result["sources"])


def test_portrait_matches_whole_name_and_linked_context(client):
    person = record(client, "person", name="Ann", aliases=["Annie"])
    unrelated = save(client, "I was planning a journey through a canyon.")
    related = save(client, "Annie met me at the gate.")
    note = record(
        client,
        "answer",
        question="Our relationship?",
        answer="We met at school",
        person_id=person["id"],
    )
    result = generate(client, "portrait", subject_id=person["id"])
    assert related["id"] in result["scope"]["included_dream_ids"]
    assert unrelated["id"] not in result["scope"]["included_dream_ids"]
    assert note["id"] in [s["id"] for s in result["sources"]]


def test_unknown_or_changed_quotes_are_rejected_and_originals_survive(client):
    dream = save(client, "I found a garden.")
    provider = client.app.state.providers["codex"]
    original = provider.run

    async def fabricated(request, folder):
        result = await original(request, folder)
        result.output["sections"][0]["evidence"][0]["quote"] = "Invented event"
        return result

    provider.run = fabricated
    job = client.post(
        "/api/insights/runs",
        json={
            "kind": "weekly",
            "provider": "codex",
            "date_from": "2026-09-05",
            "date_to": "2026-09-11",
        },
    ).json()
    done = finish(client, job["id"])
    assert done["state"] == "failed"
    assert done["error_code"] == "invalid_evidence"
    assert client.get("/api/insights/runs").json() == []
    assert client.get("/api/dreams/" + dream["id"]).json()["text"] == "I found a garden."


def test_source_change_during_generation_does_not_save_current_result(client):
    answer = record(client, "answer", question="How are things?", answer="Busy")
    provider = client.app.state.providers["codex"]
    original = provider.run

    async def changed(request, folder):
        from dreamlit.insights.store import InsightStore

        InsightStore(client.app.state.store).update_record(
            answer["id"], 1, {**answer["data"], "answer": "Quiet"}
        )
        return await original(request, folder)

    provider.run = changed
    job = client.post("/api/insights/runs", json={"kind": "question", "provider": "codex"}).json()
    assert finish(client, job["id"])["state"] == "failed"
    assert client.get("/api/insights/runs").json() == []


def test_provider_failure_preserves_investigation_and_never_falls_back(client):
    inquiry = record(client, "investigation", question="When do I ask for help?")

    async def fail(request, folder):
        raise ProviderError("usage_limit", "Limit reached")

    client.app.state.providers["codex"].run = fail
    job = client.post(
        "/api/insights/runs",
        json={"kind": "investigation", "subject_id": inquiry["id"], "provider": "codex"},
    ).json()
    assert finish(client, job["id"])["error_code"] == "usage_limit"
    assert (
        client.get("/api/insights/records/" + inquiry["id"]).json()["data"]["question"]
        == inquiry["data"]["question"]
    )
    assert client.get("/api/insights/runs").json() == []


def test_complete_source_budget_and_excluded_subject(tmp_path):
    from dreamlit.insights.sources import select_sources

    sources = [
        dict(
            kind="dream",
            id=str(i),
            revision=1,
            date=f"2026-09-{i + 1:02}",
            label="Dream",
            fields={"text": "x" * 500},
        )
        for i in range(5)
    ]
    selected, scope = select_sources(sources, "turning_points", max_chars=1600)
    assert len(selected) == 2
    assert len(json.dumps(selected, ensure_ascii=False)) <= 1600
    assert scope["truncated"]
    assert scope["total_eligible_dreams"] == 5


def test_deleted_dream_removes_generated_letter(client):
    dream = save(client, "A small bird followed me.")
    run = generate(client, "weekly", date_from="2026-09-05", date_to="2026-09-11")
    client.delete("/api/dreams/" + dream["id"])
    assert client.get("/api/insights/runs/" + run["id"]).status_code == 404


def test_existing_scan_includes_personal_context(client):
    record(client, "answer", question="What is happening?", answer="I moved cities")
    save(client, "I was looking for my street.")
    save(client, "I recognised my new door.")
    requests = []
    provider = client.app.state.providers["codex"]
    original = provider.run

    async def capture(request, folder):
        requests.append(request)
        return await original(request, folder)

    provider.run = capture
    job = client.post("/api/scan", json={"provider": "codex"}).json()
    assert finish(client, job["id"])["state"] == "completed"
    assert all(r.payload["personal_context"] for r in requests if r.task in ("extract", "connect"))
