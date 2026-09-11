import json

from pydantic import Field

from ..insights.sources import personal_context
from ..models import AnalysisOutput, ContextSnapshot, Scope, StrictModel
from ..providers.base import ProviderRequest
from .evidence import validate_analysis
from .prompts import CORE


class Groups(StrictModel):
    groups: list[list[str]] = Field(max_length=12)


async def scan_history(service, payload, provider, job_id, job_dir):
    store = service.store
    dreams = [
        d
        for d in store.list_dreams()
        if d.text.strip()
        and (not payload.get("date_from") or str(d.dreamed_on) >= payload["date_from"])
        and (not payload.get("date_to") or str(d.dreamed_on) <= payload["date_to"])
    ]
    if len(dreams) < 2:
        raise ValueError("Save at least two dreams in this date range before scanning.")
    current = {d.id: d for d in dreams}
    cached = {}
    for a in reversed(store.list_analyses()):
        if a["stale"]:
            continue
        # A single-source extraction is the reusable checkpoint. Connection
        # responses may omit observations and must not erase that index.
        if len(a["source_revisions"]) != 1:
            continue
        for dream_id in a["source_revisions"]:
            cached[dream_id] = [
                o
                for o in a["output"]["observations"]
                if any(r["dream_id"] == dream_id for r in o["evidence"])
            ]
    index = []
    for number, dream in enumerate(dreams, 1):
        store.set_job(job_id, stage=f"Building history index {number} of {len(dreams)}")
        if dream.id not in cached:
            scope = Scope(
                included_dream_ids=[dream.id],
                total_eligible_dreams=len(dreams),
                truncated=True,
            )
            context = ContextSnapshot(
                dreams=[dream],
                associations=store.list_associations(),
                feedback=store.list_feedback(),
                personal_context=personal_context(store, dream.text),
                scope=scope,
            )
            result = await service.call("extract", context, provider, job_dir)
            output = validate_analysis(
                AnalysisOutput.model_validate(result.output), {dream.id: dream}
            )
            output.patterns = []
            store.save_analysis(
                job_id,
                provider,
                result.model,
                [dream],
                scope,
                output,
                personal_context=context.personal_context,
            )
            cached[dream.id] = [o.model_dump() for o in output.observations]
        index.append({"dream_id": dream.id, "observations": cached[dream.id]})
    # Describe rather than quote at this candidate stage; originals are checked below.
    compact = [
        {
            "dream_id": x["dream_id"],
            "situations": [{"kind": o["kind"], "label": o["label"]} for o in x["observations"]],
        }
        for x in index
    ]
    if len(json.dumps(compact)) > 60000:
        raise ValueError(
            "This history index is too large for one scan. Choose a narrower date range; completed extractions are saved."
        )
    store.set_job(job_id, stage="Comparing situations across your history")
    prompt = (
        CORE
        + "\nFor this task, return groups of 2 to 8 distinct dream IDs with similar emotional situations, based on the supplied descriptions. These are candidate groups for later verification. Include non-adjacent dates. No group is required."
    )
    request = ProviderRequest(
        "group",
        prompt,
        {"index": compact},
        Groups.model_json_schema(),
        getattr(store.preferences(), provider + "_model") or None,
    )
    result = await service.providers[provider].run(request, job_dir)
    groups = Groups.model_validate(result.output).groups
    last_id = None
    skipped = 0
    for number, group in enumerate(groups, 1):
        ids = list(dict.fromkeys(group))
        if len(ids) < 2 or len(ids) > 8 or any(i not in current for i in ids):
            raise ValueError("The scan returned an invalid candidate group. Please retry.")
        sources = [current[i] for i in ids]
        if sum(len(d.text) + len(d.context) for d in sources) > 60000:
            skipped += 1
            continue
        store.set_job(job_id, stage=f"Verifying original passages {number} of {len(groups)}")
        scope = Scope(
            included_dream_ids=ids,
            total_eligible_dreams=len(dreams),
            truncated=len(ids) < len(dreams),
        )
        context = ContextSnapshot(
            dreams=sources,
            associations=store.list_associations(),
            feedback=store.list_feedback(),
            personal_context=personal_context(store, " ".join(d.text for d in sources)),
            scope=scope,
        )
        result = await service.call("connect", context, provider, job_dir)
        output = validate_analysis(
            AnalysisOutput.model_validate(result.output), {d.id: d for d in sources}
        )
        last_id = store.save_analysis(
            job_id,
            provider,
            result.model,
            sources,
            scope,
            output,
            personal_context=context.personal_context,
        )["id"]
    store.set_job(
        job_id,
        stage=f"Scan finished: {len(dreams)} dreams indexed, {len(groups) - skipped} candidate groups checked, {skipped} skipped",
    )
    return last_id
