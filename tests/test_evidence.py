import pytest
from dreamlit.analysis.evidence import EvidenceError, validate_analysis
from dreamlit.models import AnalysisOutput, Dream


def sources():
    return {
        k: Dream(
            id=k,
            dreamed_on="2026-09-09",
            text=t,
            context="",
            revision=1,
            audio_id=None,
            created_at="now",
        )
        for k, t in [
            ("a", "The phone would not dial."),
            ("b", "Nobody heard me at dinner."),
        ]
    }


def output():
    return AnalysisOutput(
        summary="Communication",
        observations=[],
        patterns=[
            dict(
                key="p",
                title="Trying to communicate",
                observation="Communication fails.",
                hypothesis=None,
                question="Does this happen awake?",
                alternatives=[],
                counterevidence=[],
                evidence=[
                    dict(
                        dream_id="a",
                        revision=1,
                        field="text",
                        quote="The phone would not dial.",
                    ),
                    dict(
                        dream_id="b",
                        revision=1,
                        field="text",
                        quote="Nobody heard me at dinner.",
                    ),
                ],
            )
        ],
    )


def test_valid_and_empty_outputs():
    assert validate_analysis(output(), sources()).patterns
    assert (
        validate_analysis(
            AnalysisOutput(summary="", observations=[], patterns=[]), sources()
        ).patterns
        == []
    )


@pytest.mark.parametrize(
    "change,reason",
    [
        (dict(quote="My father took the phone."), "quote"),
        (dict(dream_id="x"), "unknown"),
        (dict(revision=2), "revision"),
    ],
)
def test_unsupported_evidence_is_rejected(change, reason):
    data = output().model_dump()
    data["patterns"][0]["evidence"][0].update(change)
    with pytest.raises(EvidenceError, match=reason):
        validate_analysis(AnalysisOutput(**data), sources())


def test_two_quotes_from_one_dream_are_not_a_recurrence():
    data = output().model_dump()
    data["patterns"][0]["evidence"][1] = data["patterns"][0]["evidence"][0]
    with pytest.raises(EvidenceError, match="distinct"):
        validate_analysis(AnalysisOutput(**data), sources())


def test_counterexample_does_not_count_as_a_second_supporting_dream():
    data = output().model_dump()
    pattern = data["patterns"][0]
    pattern["counterevidence"] = [pattern["evidence"][1]]
    pattern["evidence"][1] = pattern["evidence"][0]
    with pytest.raises(EvidenceError, match="distinct"):
        validate_analysis(AnalysisOutput(**data), sources())


def test_counterexample_quote_must_match_its_source():
    data = output().model_dump()
    data["patterns"][0]["counterevidence"] = [
        dict(dream_id="a", revision=1, field="text", quote="The phone worked.")
    ]
    with pytest.raises(EvidenceError, match="quote"):
        validate_analysis(AnalysisOutput(**data), sources())
