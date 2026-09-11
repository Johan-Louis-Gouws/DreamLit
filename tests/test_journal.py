import pytest
from dreamlit.models import DreamCreate
from dreamlit.storage import Conflict, Store


def test_original_survives_restart_and_revision(tmp_path):
    first = Store(tmp_path).create_dream(
        DreamCreate(dreamed_on="2026-09-09", text="The train left.", context="")
    )
    revised = Store(tmp_path).revise_dream(
        first.id,
        1,
        DreamCreate(dreamed_on="2026-09-09", text="The boat left.", context=""),
    )
    reopened = Store(tmp_path)
    assert reopened.get_dream(first.id).text == "The boat left."
    assert revised.revision == 2
    assert reopened.get_revision(first.id, 1).text == "The train left."


def test_revision_conflict_does_not_overwrite(tmp_path):
    store = Store(tmp_path)
    entry = store.create_dream(DreamCreate(dreamed_on="2026-09-09", text="Original"))
    store.revise_dream(entry.id, 1, DreamCreate(dreamed_on="2026-09-09", text="Edited"))
    with pytest.raises(Conflict):
        store.revise_dream(entry.id, 1, DreamCreate(dreamed_on="2026-09-09", text="Stale"))
    assert store.get_dream(entry.id).text == "Edited"


def test_literal_search_and_empty_text(tmp_path):
    store = Store(tmp_path)
    entry = store.create_dream(DreamCreate(dreamed_on="2026-09-09", text="A 100% empty room"))
    assert [d.id for d in store.list_dreams("100%")] == [entry.id]
    assert store.list_dreams("' OR 1=1 --") == []
    with pytest.raises(ValueError):
        DreamCreate(dreamed_on="2026-09-09", text="  ")


def test_newer_database_is_not_silently_downgraded(tmp_path):
    import sqlite3

    import pytest

    db = sqlite3.connect(tmp_path / "journal.sqlite3")
    db.execute("PRAGMA user_version=99")
    db.close()
    with pytest.raises(ValueError, match="newer"):
        Store(tmp_path)
    db = sqlite3.connect(tmp_path / "journal.sqlite3")
    assert db.execute("PRAGMA user_version").fetchone()[0] == 99
    db.close()
