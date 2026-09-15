"""Select complete, dated sources; generated interpretations never become facts."""

import json
import re


def words(text):
    return set(re.findall(r"\w{3,}", text.casefold()))


def contains_name(text, names):
    return any(
        re.search(r"(?<!\w)" + re.escape(name.strip()) + r"(?!\w)", text, re.IGNORECASE)
        for name in names
        if name.strip()
    )


def all_sources(store):
    from .store import InsightStore

    return [
        dict(
            kind="dream",
            id=d.id,
            revision=d.revision,
            date=str(d.dreamed_on),
            label=d.text[:100],
            fields={"text": d.text, "context": d.context},
        )
        for d in store.list_dreams()
        if d.text.strip()
    ] + InsightStore(store).sources()


def select_sources(sources, kind, subject_id=None, date_from=None, date_to=None, max_chars=60000):
    subject = next((s for s in sources if s["id"] == subject_id), None)
    if subject_id and subject is None:
        raise ValueError("This record is unavailable for analysis. Review its inclusion setting.")
    eligible = [
        s
        for s in sources
        if s["kind"] != "dream"
        or ((not date_from or s["date"] >= date_from) and (not date_to or s["date"] <= date_to))
    ]
    linked_dreams = set(subject["fields"].get("dream_ids", "").splitlines()) if subject else set()
    if kind == "portrait":
        linked_dreams.update(
            s["fields"]["dream_id"]
            for s in eligible
            if s["kind"] == "answer"
            and s["fields"].get("person_id") == subject_id
            and s["fields"].get("dream_id")
        )
        names = [subject["fields"]["name"], *subject["fields"].get("aliases", "").splitlines()]
        eligible = [
            s
            for s in eligible
            if s["id"] == subject_id
            or s["fields"].get("person_id") == subject_id
            or (s["kind"] == "dream" and s["id"] in linked_dreams)
            or (
                s["kind"] == "dream"
                and contains_name(
                    s["fields"].get("text", "") + " " + s["fields"].get("context", ""), names
                )
            )
        ]
    dream_count = sum(s["kind"] == "dream" for s in eligible)
    query = words(" ".join(subject["fields"].values())) if subject else set()

    def priority(source):
        text = " ".join(source["fields"].values())
        linked = bool(subject_id and subject_id in source["fields"].values())
        return (
            source["id"] == subject_id,
            source["kind"] == "dream" and source["id"] in linked_dreams,
            linked,
            len(query & words(text)),
            source["date"],
            source["id"],
        )

    candidates = sorted(eligible, key=priority, reverse=True)
    selected = []
    selected_ids = set()
    for source in candidates:
        if source["id"] in selected_ids:
            continue
        bundle = [source]
        if kind == "portrait" and source["kind"] == "dream" and source["id"] in linked_dreams:
            identifiers = [
                s
                for s in eligible
                if s["kind"] == "answer"
                and s["fields"].get("person_id") == subject_id
                and s["fields"].get("dream_id") == source["id"]
            ]
            # An unnamed character is identified by the user's answer. Keep
            # that evidence with the dream so its exclusion invalidates the
            # portrait and the model can see why the dream was selected.
            if identifiers and not any(s["id"] in selected_ids for s in identifiers):
                bundle.append(
                    min(identifiers, key=lambda s: len(json.dumps(s, ensure_ascii=False)))
                )
        if len(json.dumps([*selected, *bundle], ensure_ascii=False)) <= max_chars:
            selected.extend(bundle)
            selected_ids.update(s["id"] for s in bundle)
        elif source["id"] == subject_id:
            raise ValueError("This record exceeds the analysis budget. Shorten its notes first.")
    return selected, dict(
        included_dream_ids=[s["id"] for s in selected if s["kind"] == "dream"],
        total_eligible_dreams=dream_count,
        truncated=len(selected) < len(eligible),
        date_from=date_from,
        date_to=date_to,
    )


def personal_context(store, query="", max_chars=12000):
    from .store import InsightStore

    terms = words(query)
    candidates = sorted(
        InsightStore(store).sources(),
        key=lambda s: (len(terms & words(" ".join(s["fields"].values()))), s["date"], s["id"]),
        reverse=True,
    )
    selected = []
    for source in candidates:
        if len(json.dumps([*selected, source], ensure_ascii=False)) <= max_chars:
            selected.append(source)
    return selected
