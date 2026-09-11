import re

from ..insights.sources import personal_context
from ..models import ContextSnapshot, Scope


def build_context(store, anchor_id, observations, max_chars=60000):
    dreams = [d for d in store.list_dreams() if d.text.strip()]
    anchor = store.get_dream(anchor_id)
    if len(anchor.text) + len(anchor.context) > max_chars:
        raise ValueError(
            "This entry exceeds the analysis context budget. Split it into shorter dreams."
        )
    tokens = set(re.findall(r"\w{4,}", " ".join(o.label for o in observations).lower()))
    prior_labels = {}
    for analysis in store.list_analyses():
        if analysis["stale"]:
            continue
        for observation in analysis["output"]["observations"]:
            for ref in observation["evidence"]:
                prior_labels.setdefault(ref["dream_id"], []).append(observation["label"])

    def score(dream):
        text = (dream.text + " " + " ".join(prior_labels.get(dream.id, []))).lower()
        return sum(token in text for token in tokens)

    candidates = sorted([d for d in dreams if d.id != anchor.id], key=score, reverse=True)
    selected = [anchor]
    used = len(anchor.text) + len(anchor.context)
    for dream in candidates:
        size = len(dream.text) + len(dream.context)
        if used + size <= max_chars:
            selected.append(dream)
            used += size
    return ContextSnapshot(
        dreams=selected,
        associations=store.list_associations(),
        feedback=store.list_feedback(),
        personal_context=personal_context(store, anchor.text),
        scope=Scope(
            included_dream_ids=[d.id for d in selected],
            total_eligible_dreams=len(dreams),
            truncated=len(selected) < len(dreams),
        ),
    )
