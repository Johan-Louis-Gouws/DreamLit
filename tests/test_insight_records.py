import io
import json
import zipfile
from datetime import date, timedelta

import pytest
from dreamlit.api import create_app
from dreamlit.config import Settings
from dreamlit.export import export_journal
from dreamlit.insights.store import InsightStore
from dreamlit.models import AnalysisOutput, DreamCreate, ReflectionOutput, Scope
from dreamlit.storage import Conflict, Store
from fastapi.testclient import TestClient


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)


@pytest.fixture
def insights(store):
    return InsightStore(store)


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client


def answer_data(**changes):
    data = {"question": " What feels unfinished? ", "answer": " Calling my sister. "}
    data.update(changes)
    return data


def output_for(source, *, quote=None):
    return {
        "title": "A reflection",
        "summary": "A short summary.",
        "sections": [
            {
                "heading": "What stands out",
                "body": "A grounded observation.",
                "evidence": [
                    {
                        "source_kind": source["kind"],
                        "source_id": source["id"],
                        "revision": source["revision"],
                        "field": next(iter(source["fields"])),
                        "quote": quote or next(iter(source["fields"].values())),
                    }
                ],
                "counterevidence": [],
            }
        ],
        "question": "What would you like to notice next?",
    }


def test_answer_api_preserves_history_rejects_stale_writes_and_excludes_sources(client):
    created = client.post(
        "/api/insights/records", json={"kind": "answer", "data": answer_data()}
    )
    assert created.status_code == 201, created.text
    original = created.json()
    assert original["data"] == {
        "question": "What feels unfinished?",
        "answer": "Calling my sister.",
        "topic": "General",
        "scope": "current",
        "status": "current",
        "dream_id": None,
        "person_id": None,
        "audio_id": None,
    }

    changed_data = answer_data(answer="I called her.", status="changed")
    changed = client.put(
        f"/api/insights/records/{original['id']}",
        json={"expected_revision": 1, "data": changed_data},
    )
    assert changed.status_code == 200
    assert changed.json()["revision"] == 2
    stale = client.put(
        f"/api/insights/records/{original['id']}",
        json={"expected_revision": 1, "data": answer_data(answer="Overwrite")},
    )
    assert stale.status_code == 409

    history = client.get(f"/api/insights/records/{original['id']}/history").json()
    assert [item["revision"] for item in history] == [2, 1]
    assert history[1]["data"]["answer"] == "Calling my sister."
    assert InsightStore(client.app.state.store).sources() == []


def test_links_require_existing_records_and_deletion_clears_live_links(insights):
    with pytest.raises(ValueError, match="person"):
        insights.create_record("answer", answer_data(person_id="missing"))

    person = insights.create_record(
        "person", {"name": " Sam ", "aliases": [" Sammy ", "S"], "notes": " Family. "}
    )
    investigation = insights.create_record(
        "investigation", {"question": "Why do I avoid asking?"}
    )
    answer = insights.create_record("answer", answer_data(person_id=person["id"]))
    experiment = insights.create_record(
        "experiment",
        {
            "action": "Ask directly",
            "person_id": person["id"],
            "investigation_id": investigation["id"],
        },
    )

    insights.delete_record(person["id"])
    assert insights.get_record(answer["id"])["data"]["person_id"] is None
    revised_experiment = insights.get_record(experiment["id"])
    assert revised_experiment["revision"] == 2
    assert revised_experiment["data"]["person_id"] is None
    assert revised_experiment["data"]["investigation_id"] == investigation["id"]
    assert insights.record_history(answer["id"])[-1]["data"]["person_id"] == person["id"]


@pytest.mark.parametrize(
    ("kind", "data"),
    [
        ("answer", {"question": "Q", "answer": "a" * 10001}),
        ("person", {"name": "n" * 201}),
        ("person", {"name": "Sam", "aliases": [str(index) for index in range(33)]}),
        (
            "investigation",
            {"question": "Q", "dream_ids": [str(index) for index in range(201)]},
        ),
        ("experiment", {"action": "Try", "outcome": "o" * 10001}),
    ],
)
def test_record_payloads_have_bounded_text_and_link_arrays(insights, kind, data):
    with pytest.raises(ValueError, match="at most"):
        insights.create_record(kind, data)


def test_sources_have_stable_public_shape_and_omit_ineligible_records(insights, store):
    dream = store.create_dream(
        DreamCreate(dreamed_on="2026-09-03", text="I saw Sam.", context="At home")
    )
    person = insights.create_record(
        "person",
        {
            "name": " Sam ",
            "aliases": [" Sammy ", " S. "],
            "relationship": " sibling ",
            "notes": " We speak weekly. ",
        },
    )
    answer = insights.create_record(
        "answer", answer_data(person_id=person["id"], dream_id=dream.id)
    )
    insights.create_record("person", {"name": "Private", "include_in_analysis": False})

    sources = {source["id"]: source for source in insights.sources()}
    assert set(sources) == {person["id"], answer["id"]}
    assert sources[person["id"]] == {
        "kind": "person",
        "id": person["id"],
        "revision": 1,
        "date": person["updated_at"][:10],
        "label": "Sam",
        "fields": {
            "name": "Sam",
            "aliases": "Sammy\nS.",
            "relationship": "sibling",
            "notes": "We speak weekly.",
        },
    }
    assert sources[answer["id"]]["fields"]["person_id"] == person["id"]
    assert sources[answer["id"]]["fields"]["dream_id"] == dream.id


def test_run_save_is_atomic_validates_quotes_and_tracks_source_lifecycle(insights):
    answer = insights.create_record("answer", answer_data())
    source = next(item for item in insights.sources() if item["id"] == answer["id"])
    scope = {
        "included_dream_ids": [],
        "total_eligible_dreams": 0,
        "truncated": False,
        "date_from": None,
        "date_to": None,
    }

    with pytest.raises(ValueError, match="quote"):
        insights.save_run(
            "question", None, "codex", "fixture", output_for(source, quote="fabricated"), [source], scope
        )
    assert insights.list_runs() == []

    run = insights.save_run(
        "question", None, "codex", "fixture", output_for(source), [source], scope
    )
    assert run["sources"] == [source]
    assert run["stale"] is False
    insights.update_record(answer["id"], 1, answer_data(answer="A new answer."))
    assert insights.get_run(run["id"])["stale"] is True

    current_source = next(item for item in insights.sources() if item["id"] == answer["id"])
    stale_source = {**current_source, "revision": 1}
    with pytest.raises(Conflict, match="changed"):
        insights.save_run(
            "question",
            None,
            "codex",
            "fixture",
            output_for(stale_source),
            [stale_source],
            scope,
        )
    insights.delete_record(answer["id"])
    with pytest.raises(KeyError):
        insights.get_run(run["id"])


def test_personal_context_dependencies_invalidate_and_delete_old_analyses(insights, store):
    dream = store.create_dream(DreamCreate(dreamed_on="2026-09-02", text="A blue door"))
    answer = insights.create_record("answer", answer_data())
    personal = [next(item for item in insights.sources() if item["id"] == answer["id"])]
    analysis = store.save_analysis(
        "job-id",
        "codex",
        "fixture",
        [dream],
        Scope(included_dream_ids=[dream.id], total_eligible_dreams=1, truncated=False),
        AnalysisOutput(summary="No pattern", observations=[], patterns=[]),
        personal_context=personal,
    )
    assert analysis["personal_context_sources"] == [
        {
            "kind": "answer",
            "id": answer["id"],
            "revision": 1,
            "label": "What feels unfinished?",
        }
    ]

    insights.update_record(answer["id"], 1, answer_data(answer="Different"))
    assert store.get_analysis(analysis["id"])["stale"] is True
    insights.delete_record(answer["id"])
    with pytest.raises(KeyError):
        store.get_analysis(analysis["id"])


def test_reflection_personal_context_is_reported_staled_and_removed(insights, store):
    first = store.create_dream(DreamCreate(dreamed_on="2026-09-01", text="A blue door"))
    second = store.create_dream(DreamCreate(dreamed_on="2026-09-02", text="A red door"))
    answer = insights.create_record("answer", answer_data())
    personal = [next(item for item in insights.sources() if item["id"] == answer["id"])]
    references = [
        {"dream_id": first.id, "revision": 1, "field": "text", "quote": "A blue door"},
        {"dream_id": second.id, "revision": 1, "field": "text", "quote": "A red door"},
    ]
    analysis = store.save_analysis(
        "job-id",
        "codex",
        "fixture",
        [first, second],
        Scope(
            included_dream_ids=[first.id, second.id],
            total_eligible_dreams=2,
            truncated=False,
        ),
        AnalysisOutput(
            summary="Doors recur.",
            observations=[],
            patterns=[
                {
                    "key": "doors",
                    "title": "Doors",
                    "observation": "Two doors appeared.",
                    "hypothesis": None,
                    "question": "What might they mark?",
                    "alternatives": [],
                    "evidence": references,
                    "counterevidence": [],
                }
            ],
        ),
    )
    pattern_id = analysis["patterns"][0]["id"]
    reflection_id = store.save_reflection(
        pattern_id,
        "codex",
        "Consider my own answer.",
        ReflectionOutput(response="Notice the unfinished call.", evidence=[]),
        personal_context=personal,
    )
    reflection = store.get_pattern(pattern_id)["reflections"][0]
    assert reflection["id"] == reflection_id
    assert reflection["stale"] is False
    assert reflection["personal_context_sources"] == [
        {
            "kind": "answer",
            "id": answer["id"],
            "revision": 1,
            "label": "What feels unfinished?",
        }
    ]

    insights.update_record(answer["id"], 1, answer_data(answer="Different"))
    assert store.get_pattern(pattern_id)["reflections"][0]["stale"] is True
    insights.delete_record(answer["id"])
    assert store.get_pattern(pattern_id)["reflections"] == []


def test_export_contains_current_records_history_runs_and_source_metadata(insights, tmp_path):
    answer = insights.create_record("answer", answer_data())
    source = insights.sources()[0]
    run = insights.save_run(
        "question",
        None,
        "codex",
        "fixture",
        output_for(source),
        [source],
        {
            "included_dream_ids": [],
            "total_eligible_dreams": 0,
            "truncated": False,
            "date_from": None,
            "date_to": None,
        },
    )
    target = tmp_path / "export.zip"
    export_journal(insights.store, target)
    with zipfile.ZipFile(io.BytesIO(target.read_bytes())) as archive:
        exported = json.loads(archive.read("journal.json"))
    assert exported["insight_records"][0]["id"] == answer["id"]
    assert exported["insight_record_revisions"][0]["record_id"] == answer["id"]
    assert exported["insight_runs"][0]["id"] == run["id"]
    assert exported["insight_run_sources"][0]["source_id"] == answer["id"]


def test_run_api_validates_subjects_and_weekly_period_before_enqueue(client):
    person = client.post(
        "/api/insights/records", json={"kind": "person", "data": {"name": "Sam"}}
    ).json()
    excluded = client.post(
        "/api/insights/records",
        json={"kind": "person", "data": {"name": "Lee", "include_in_analysis": False}},
    ).json()
    investigation = client.post(
        "/api/insights/records",
        json={"kind": "investigation", "data": {"question": "What changed?"}},
    ).json()

    assert client.post("/api/insights/runs", json={"kind": "portrait", "provider": "codex"}).status_code == 422
    assert (
        client.post(
            "/api/insights/runs",
            json={"kind": "portrait", "provider": "codex", "subject_id": investigation["id"]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/insights/runs",
            json={"kind": "portrait", "provider": "codex", "subject_id": excluded["id"]},
        ).status_code
        == 422
    )
    accepted = client.post(
        "/api/insights/runs",
        json={"kind": "portrait", "provider": "codex", "subject_id": person["id"]},
    )
    assert accepted.status_code == 202
    assert "payload" not in accepted.json()

    assert (
        client.post(
            "/api/insights/runs",
            json={"kind": "weekly", "provider": "codex", "date_from": "2026-09-01"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/insights/runs",
            json={
                "kind": "weekly",
                "provider": "codex",
                "date_from": "2026-09-01",
                "date_to": "2026-09-08",
            },
        ).status_code
        == 422
    )
    weekly = client.post("/api/insights/runs", json={"kind": "weekly", "provider": "codex"})
    assert weekly.status_code == 202
    payload = client.app.state.store.get_job(weekly.json()["id"])["payload"]
    assert date.fromisoformat(payload["date_to"]) - date.fromisoformat(payload["date_from"]) == timedelta(days=6)
