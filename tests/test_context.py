from dreamlit.analysis.context import build_context
from dreamlit.models import DreamCreate
from dreamlit.storage import Store


def test_budget_reports_omissions_and_includes_anchor(tmp_path):
    store = Store(tmp_path)
    dreams = [
        store.create_dream(
            DreamCreate(dreamed_on="2026-09-09", text=("Different dream " + str(i) + " ") * 100)
        )
        for i in range(10)
    ]
    snapshot = build_context(store, dreams[-1].id, [], max_chars=3000)
    assert dreams[-1].id in snapshot.scope.included_dream_ids
    assert snapshot.scope.total_eligible_dreams == 10
    assert snapshot.scope.truncated is True
    assert len(snapshot.dreams) < 10


def test_feedback_and_associations_stay_user_supplied(tmp_path):
    store = Store(tmp_path)
    dream = store.create_dream(DreamCreate(dreamed_on="2026-09-09", text="At school again."))
    store.add_association("School", "A place I enjoyed", dream.id)
    context = build_context(store, dream.id, [])
    assert context.associations[0]["meaning"] == "A place I enjoyed"
