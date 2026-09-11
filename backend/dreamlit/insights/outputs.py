from typing import Literal

from pydantic import Field

from ..analysis.evidence import EvidenceError
from ..models import StrictModel


class InsightEvidence(StrictModel):
    source_kind: Literal["dream", "answer", "person", "investigation", "experiment"]
    source_id: str
    revision: int = Field(ge=1)
    field: str
    quote: str = Field(min_length=1, max_length=10000)


class InsightSection(StrictModel):
    heading: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    evidence: list[InsightEvidence] = Field(min_length=1, max_length=12)
    counterevidence: list[InsightEvidence] = Field(max_length=12)


class InsightOutput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(max_length=3000)
    sections: list[InsightSection] = Field(max_length=6)
    question: str = Field(min_length=1, max_length=1000)


def validate_output(raw, sources, kind):
    output = InsightOutput.model_validate(raw)
    available = {(s["kind"], s["id"]): s for s in sources}
    for section in output.sections:
        for ref in section.evidence + section.counterevidence:
            source = available.get((ref.source_kind, ref.source_id))
            if source is None or source["revision"] != ref.revision:
                raise EvidenceError("Unknown or outdated insight source")
            text = source["fields"].get(ref.field)
            if not text or not ref.quote.strip() or ref.quote not in text:
                raise EvidenceError("The insight quotation does not match its source")
        if kind == "turning_points":
            dreams = {ref.source_id for ref in section.evidence if ref.source_kind == "dream"}
            if len(dreams) < 2:
                raise EvidenceError("A turning point needs at least two distinct dream passages")
            if len({available[("dream", ident)]["date"] for ident in dreams}) < 2:
                raise EvidenceError("A turning point needs dreams from distinct dates")
    return output
