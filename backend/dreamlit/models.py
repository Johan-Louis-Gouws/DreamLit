from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProviderName = Literal["codex", "claude"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DreamCreate(StrictModel):
    dreamed_on: date
    text: str = Field(min_length=1, max_length=50000)
    context: str = Field(default="", max_length=10000)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Write something you remember first.")
        return value


class DreamUpdate(DreamCreate):
    expected_revision: int = Field(ge=1)


class Dream(StrictModel):
    id: str
    dreamed_on: date
    text: str
    context: str
    revision: int
    audio_id: str | None
    created_at: str


class EvidenceRef(StrictModel):
    dream_id: str
    revision: int
    field: Literal["text", "context"]
    quote: str = Field(min_length=1)


class Observation(StrictModel):
    key: str
    kind: Literal[
        "character",
        "place",
        "emotion",
        "goal",
        "obstacle",
        "response",
        "social_interaction",
        "outcome",
    ]
    label: str
    inferred: bool
    evidence: list[EvidenceRef] = Field(min_length=1)


class Pattern(StrictModel):
    key: str
    title: str
    observation: str
    hypothesis: str | None
    question: str
    alternatives: list[str]
    evidence: list[EvidenceRef] = Field(min_length=2)
    counterevidence: list[EvidenceRef]


class AnalysisOutput(StrictModel):
    summary: str
    observations: list[Observation]
    patterns: list[Pattern]


class ReflectionOutput(StrictModel):
    response: str
    evidence: list[EvidenceRef]


class Scope(StrictModel):
    included_dream_ids: list[str]
    total_eligible_dreams: int
    truncated: bool


class ContextSnapshot(StrictModel):
    dreams: list[Dream]
    associations: list[dict]
    feedback: list[dict]
    scope: Scope
    personal_context: list[dict] = Field(default_factory=list)


class AnalyseRequest(StrictModel):
    provider: ProviderName


class ReflectionRequest(AnalyseRequest):
    message: str = Field(min_length=1, max_length=10000)


class FeedbackRequest(StrictModel):
    verdict: Literal["resonates", "does_not_fit", "unsure"]
    note: str = Field(default="", max_length=10000)


class AssociationRequest(StrictModel):
    label: str = Field(min_length=1, max_length=200)
    meaning: str = Field(min_length=1, max_length=5000)
    dream_id: str | None = None


class Preferences(StrictModel):
    provider: ProviderName = "codex"
    codex_model: str = ""
    claude_model: str = ""
    whisper_binary: str = ""
    whisper_model: str = ""
    ffmpeg_binary: str = "ffmpeg"


class ScanRequest(AnalyseRequest):
    date_from: date | None = None
    date_to: date | None = None


class TranscriptAcceptance(StrictModel):
    transcript_id: str
    text: str = Field(min_length=1, max_length=50000)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value):
        return DreamCreate.not_blank(value)


class ExportRequest(StrictModel):
    include_audio: bool = False
