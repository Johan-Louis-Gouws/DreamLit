from ..models import AnalysisOutput, ReflectionOutput


class EvidenceError(ValueError):
    pass


def check_reference(ref, sources):
    source = sources.get(ref.dream_id)
    if source is None:
        raise EvidenceError("unknown dream in evidence")
    if source.revision != ref.revision:
        raise EvidenceError("source revision changed")
    if not ref.quote.strip() or ref.quote not in getattr(source, ref.field):
        raise EvidenceError("quote does not match source")


def validate_analysis(output: AnalysisOutput, sources):
    for collection in (output.observations, output.patterns):
        keys = [item.key for item in collection]
        if len(keys) != len(set(keys)):
            raise EvidenceError("duplicate result key")
        for item in collection:
            for ref in item.evidence:
                check_reference(ref, sources)
    for pattern in output.patterns:
        for ref in pattern.counterevidence:
            check_reference(ref, sources)
        if len({ref.dream_id for ref in pattern.evidence}) < 2:
            raise EvidenceError("a recurring pattern needs distinct dreams")
    return output


def validate_reflection(output: ReflectionOutput, sources):
    for ref in output.evidence:
        check_reference(ref, sources)
    return output
