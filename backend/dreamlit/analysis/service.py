from ..insights.sources import personal_context
from ..models import AnalysisOutput, ContextSnapshot, ReflectionOutput, Scope
from ..providers.base import ProviderRequest
from .context import build_context
from .evidence import validate_analysis, validate_reflection
from .prompts import render_prompt


class AnalysisService:
    def __init__(self, store, providers):
        self.store, self.providers = store, providers

    async def call(self, task, context, provider, job_dir, extra=None):
        prompt, payload = render_prompt(task, context)
        payload.update(extra or {})
        prefs = self.store.preferences()
        request = ProviderRequest(
            task,
            prompt,
            payload,
            (ReflectionOutput if task == "reflect" else AnalysisOutput).model_json_schema(),
            getattr(prefs, provider + "_model") or None,
        )
        return await self.providers[provider].run(request, job_dir)

    async def analyse(self, dream_id, provider, job_id, job_dir):
        dream = self.store.get_dream(dream_id)
        if not dream.text.strip():
            raise ValueError("Review a transcript or write your dream before analysing it.")
        eligible_count = sum(bool(d.text.strip()) for d in self.store.list_dreams())
        scope = Scope(
            included_dream_ids=[dream.id],
            total_eligible_dreams=eligible_count,
            truncated=eligible_count > 1,
        )
        context = ContextSnapshot(
            dreams=[dream],
            associations=self.store.list_associations(),
            feedback=self.store.list_feedback(),
            personal_context=personal_context(self.store, dream.text),
            scope=scope,
        )
        self.store.set_job(job_id, stage="Reading your dream")
        result = await self.call("extract", context, provider, job_dir)
        extraction = validate_analysis(
            AnalysisOutput.model_validate(result.output), {dream.id: dream}
        )
        # This checkpoint preserves useful extraction if the next call fails.
        extraction.patterns = []
        record = self.store.save_analysis(
            job_id,
            provider,
            result.model,
            [dream],
            scope,
            extraction,
            personal_context=context.personal_context,
        )
        self.store.set_job(job_id, stage="Finding connections")
        context = build_context(self.store, dream_id, extraction.observations)
        if len(context.dreams) < 2:
            return record["id"]
        result = await self.call("connect", context, provider, job_dir)
        output = validate_analysis(
            AnalysisOutput.model_validate(result.output),
            {d.id: d for d in context.dreams},
        )
        return self.store.save_analysis(
            job_id,
            provider,
            result.model,
            context.dreams,
            context.scope,
            output,
            personal_context=context.personal_context,
        )["id"]

    async def reflect(self, pattern_id, provider, message, job_id, job_dir, second_opinion=False):
        pattern = self.store.get_pattern(pattern_id)
        if pattern["stale"]:
            raise ValueError("This pattern uses an older entry. Re-analyse the dream first.")
        references = pattern["evidence"] + pattern.get("counterevidence", [])
        source_ids = list(dict.fromkeys(ref["dream_id"] for ref in references))
        sources = [self.store.get_dream(i) for i in source_ids]
        context = ContextSnapshot(
            dreams=sources,
            associations=self.store.list_associations(),
            feedback=self.store.list_feedback(pattern_id),
            personal_context=personal_context(self.store, pattern["question"] + " " + message),
            scope=Scope(
                included_dream_ids=source_ids,
                total_eligible_dreams=len(self.store.list_dreams()),
                truncated=len(source_ids) < len(self.store.list_dreams()),
            ),
        )
        self.store.set_job(
            job_id, stage="Considering the evidence" if second_opinion else "Reflecting"
        )
        result = await self.call(
            "reflect",
            context,
            provider,
            job_dir,
            {"pattern": pattern, "message": message, "second_opinion": second_opinion},
        )
        output = validate_reflection(
            ReflectionOutput.model_validate(result.output), {d.id: d for d in sources}
        )
        # Source revisions may change while a CLI is running.
        for dream in sources:
            if self.store.get_dream(dream.id).revision != dream.revision:
                raise ValueError(
                    "A source changed during reflection. Please retry from the current entry."
                )
        return self.store.save_reflection(
            pattern_id, provider, message, output, personal_context=context.personal_context
        )
