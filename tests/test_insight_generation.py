import json

import pytest
from dreamlit.models import AnalysisOutput, ContextSnapshot, DreamCreate, Scope
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


def test_person_exclusion_invalidates_an_indirect_answer_dependency(client):
    from dreamlit.insights.store import InsightStore
    from dreamlit.storage import Conflict

    person = record(client, "person", name="Ann", notes="long notes " * 900)
    answer = record(
        client, "answer", question="Who was there?", answer="My sister", person_id=person["id"]
    )
    store = InsightStore(client.app.state.store)
    selected = [s for s in store.sources() if s["id"] == answer["id"]]
    output = {
        "title": "A question",
        "summary": "",
        "sections": [],
        "question": "What felt familiar?",
    }
    scope = {
        "included_dream_ids": [],
        "total_eligible_dreams": 0,
        "truncated": True,
        "date_from": None,
        "date_to": None,
    }
    run = store.save_run("question", None, "codex", "fixture", output, selected, scope)
    store.update_record(person["id"], 1, {**person["data"], "include_in_analysis": False})
    assert store.get_run(run["id"])["stale"]
    with pytest.raises(Conflict):
        store.save_run("question", None, "codex", "fixture", output, selected, scope)
    dream = client.app.state.store.create_dream(
        DreamCreate(dreamed_on="2026-09-09", text="My sister was there.")
    )
    with pytest.raises(Conflict):
        client.app.state.store.save_analysis(
            "job",
            "codex",
            "fixture",
            [dream],
            Scope(included_dream_ids=[dream.id], total_eligible_dreams=1, truncated=False),
            AnalysisOutput(summary="", observations=[], patterns=[]),
            personal_context=selected,
        )


def test_explicit_investigation_dream_survives_source_budget(client):
    from dreamlit.insights.sources import all_sources, select_sources

    pinned = client.post(
        "/api/dreams", json={"dreamed_on": "2025-01-01", "text": "An earlier dream. " + "x" * 19000}
    ).json()
    for day in ("01", "02", "03"):
        client.post(
            "/api/dreams",
            json={"dreamed_on": "2026-09-" + day, "text": "Recent dream. " + "x" * 19000},
        )
    inquiry = record(
        client, "investigation", question="What has changed?", dream_ids=[pinned["id"]]
    )
    selected, scope = select_sources(
        all_sources(client.app.state.store), "investigation", inquiry["id"]
    )
    assert pinned["id"] in [s["id"] for s in selected]
    assert scope["truncated"]


def test_portrait_uses_user_identification_of_an_unnamed_dream_character(client):
    person = record(client, "person", name="Ann")
    dream = save(client, "My sister met me at the gate.")
    record(
        client,
        "answer",
        question="Who was your sister?",
        answer="Ann",
        person_id=person["id"],
        dream_id=dream["id"],
    )
    run = generate(client, "portrait", subject_id=person["id"])
    assert dream["id"] in run["scope"]["included_dream_ids"]


def test_portrait_budget_keeps_character_identification_with_each_unnamed_dream(client):
    from dreamlit.insights.sources import all_sources, select_sources
    from dreamlit.insights.store import InsightStore
    from dreamlit.storage import Conflict

    person = record(client, "person", name="Ann")
    links = {}
    for day in ("08", "09", "10"):
        dream = client.post(
            "/api/dreams",
            json={"dreamed_on": "2026-09-" + day, "text": "My sister met me. " + "x" * 19000},
        ).json()
        answer = record(
            client,
            "answer",
            question="Who was there?",
            answer="My sister was Ann. " + "x" * 9500,
            person_id=person["id"],
            dream_id=dream["id"],
        )
        links[dream["id"]] = answer
    selected, scope = select_sources(all_sources(client.app.state.store), "portrait", person["id"])
    selected_ids = {s["id"] for s in selected}
    assert scope["included_dream_ids"]
    assert all(links[dream_id]["id"] in selected_ids for dream_id in scope["included_dream_ids"])
    assert len(json.dumps(selected, ensure_ascii=False)) <= 60000
    store = InsightStore(client.app.state.store)
    output = {"title": "Portrait", "summary": "", "sections": [], "question": "What felt familiar?"}
    run = store.save_run("portrait", person["id"], "codex", "fixture", output, selected, scope)
    answer = links[scope["included_dream_ids"][0]]
    store.update_record(answer["id"], 1, {**answer["data"], "status": "excluded"})
    assert store.get_run(run["id"])["stale"]
    with pytest.raises(Conflict):
        store.save_run("portrait", person["id"], "codex", "fixture", output, selected, scope)
