from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RecordKind = Literal["answer", "person", "investigation", "experiment"]
RunKind = Literal["question", "turning_points", "investigation", "portrait", "weekly"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _trim(value):
    return value.strip() if isinstance(value, str) else value


def _optional_id(value):
    value = _trim(value)
    return value or None


class AnswerData(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=10000)
    topic: str = Field(default="General", min_length=1, max_length=200)
    scope: Literal["ongoing", "current", "dream"] = "current"
    status: Literal["current", "changed", "excluded"] = "current"
    dream_id: str | None = None
    person_id: str | None = None
    audio_id: str | None = None

    @field_validator("question", "answer", "topic", mode="before")
    @classmethod
    def trim_text(cls, value):
        return _trim(value)

    @field_validator("dream_id", "person_id", "audio_id", mode="before")
    @classmethod
    def trim_ids(cls, value):
        return _optional_id(value)


class PersonData(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    aliases: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=32
    )
    relationship: str = Field(default="", max_length=10000)
    notes: str = Field(default="", max_length=10000)
    include_in_analysis: bool = True

    @field_validator("name", "relationship", "notes", mode="before")
    @classmethod
    def trim_text(cls, value):
        return _trim(value)

    @field_validator("aliases", mode="before")
    @classmethod
    def trim_aliases(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        aliases = []
        for item in value:
            alias = _trim(item)
            if alias and alias not in aliases:
                aliases.append(alias)
        return aliases


class InvestigationData(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    notes: str = Field(default="", max_length=10000)
    conclusion: str = Field(default="", max_length=10000)
    status: Literal["open", "resolved", "archived"] = "open"
    dream_ids: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("question", "notes", "conclusion", mode="before")
    @classmethod
    def trim_text(cls, value):
        return _trim(value)

    @field_validator("dream_ids", mode="before")
    @classmethod
    def trim_dream_ids(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        ids = []
        for item in value:
            dream_id = _trim(item)
            if dream_id and dream_id not in ids:
                ids.append(dream_id)
        return ids


class ExperimentData(StrictModel):
    action: str = Field(min_length=1, max_length=2000)
    intention: str = Field(default="", max_length=10000)
    outcome: str = Field(default="", max_length=10000)
    due_on: date | None = None
    status: Literal["planned", "active", "completed", "dropped"] = "planned"
    investigation_id: str | None = None
    person_id: str | None = None

    @field_validator("action", "intention", "outcome", mode="before")
    @classmethod
    def trim_text(cls, value):
        return _trim(value)

    @field_validator("investigation_id", "person_id", mode="before")
    @classmethod
    def trim_ids(cls, value):
        return _optional_id(value)


RECORD_MODELS = {
    "answer": AnswerData,
    "person": PersonData,
    "investigation": InvestigationData,
    "experiment": ExperimentData,
}


def validate_record_data(kind: str, data: dict) -> dict:
    try:
        model = RECORD_MODELS[kind]
    except KeyError as error:
        raise ValueError("Unknown insight record kind.") from error
    return model.model_validate(data).model_dump(mode="json")


class RecordCreate(StrictModel):
    kind: RecordKind
    data: dict


class RecordUpdate(StrictModel):
    expected_revision: int = Field(ge=1)
    data: dict


class RunCreate(StrictModel):
    kind: RunKind
    provider: Literal["codex", "claude"]
    subject_id: str | None = None
    date_from: date | None = None
    date_to: date | None = None

    @field_validator("subject_id", mode="before")
    @classmethod
    def trim_subject(cls, value):
        return _optional_id(value)
