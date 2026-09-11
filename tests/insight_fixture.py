"""Deterministic generation for integration tests, never personal interpretation."""

from dreamlit.providers.base import ProviderResponse


def response(request):
    kind = request.task.removeprefix("insight_")
    sources = request.payload["sources"]
    dreams = sorted([s for s in sources if s["kind"] == "dream"], key=lambda s: s["date"])
    chosen = dreams[:2] if kind == "turning_points" else dreams[:2] or sources[:1]
    refs = []
    for source in chosen:
        field = next(
            (
                name
                for name in ("text", "answer", "notes", "question", "name", "action")
                if source["fields"].get(name)
            ),
            None,
        )
        if field:
            refs.append(
                dict(
                    source_kind=source["kind"],
                    source_id=source["id"],
                    revision=source["revision"],
                    field=field,
                    quote=source["fields"][field],
                )
            )
    titles = {
        "question": "A question for your world",
        "turning_points": "A different response",
        "investigation": "Examples and possibilities",
        "portrait": "A relationship in your words",
        "weekly": "A letter from your week",
    }
    return ProviderResponse(
        {
            "title": titles[kind],
            "summary": "These passages offer a place to reflect."
            if refs
            else "Start with what is on your mind.",
            "sections": [
                {
                    "heading": "In your own words",
                    "body": "Compare the situations you described and what you wanted to do.",
                    "evidence": refs,
                    "counterevidence": [],
                }
            ]
            if refs and kind != "question"
            else [],
            "question": "What feels different for you now?",
        },
        "fixture",
    )
