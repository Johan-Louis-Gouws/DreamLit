from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, Request

from ..storage import Conflict
from .records import RecordCreate, RecordKind, RecordUpdate, RunCreate, RunKind
from .store import InsightStore

router = APIRouter(prefix="/api/insights", tags=["insights"])


def _store(request):
    return InsightStore(request.app.state.store)


def _validation_error(error):
    raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/records", status_code=201)
def create_record(request: Request, payload: RecordCreate):
    try:
        return _store(request).create_record(payload.kind, payload.data)
    except ValueError as error:
        _validation_error(error)


@router.get("/records")
def list_records(request: Request, kind: RecordKind | None = Query(default=None)):
    return _store(request).list_records(kind)


@router.get("/records/{record_id}")
def get_record(request: Request, record_id: str):
    return _store(request).get_record(record_id)


@router.put("/records/{record_id}")
def update_record(request: Request, record_id: str, payload: RecordUpdate):
    try:
        return _store(request).update_record(
            record_id, payload.expected_revision, payload.data
        )
    except Conflict:
        raise
    except ValueError as error:
        _validation_error(error)


@router.delete("/records/{record_id}")
def delete_record(request: Request, record_id: str):
    return _store(request).delete_record(record_id)


@router.get("/records/{record_id}/history")
def record_history(request: Request, record_id: str):
    return _store(request).record_history(record_id)


def _effective_run_payload(insights, payload):
    data = payload.model_dump(mode="json", exclude={"provider"})
    required_kind = {"investigation": "investigation", "portrait": "person"}.get(
        payload.kind
    )
    if required_kind:
        if not payload.subject_id:
            raise HTTPException(422, f"{payload.kind.title()} requires a subject.")
        try:
            subject = insights.get_record(payload.subject_id)
        except KeyError as error:
            raise HTTPException(422, f"{payload.kind.title()} subject was not found.") from error
        if subject["kind"] != required_kind:
            raise HTTPException(422, f"{payload.kind.title()} requires a {required_kind} subject.")
        if payload.kind == "portrait" and not subject["data"]["include_in_analysis"]:
            raise HTTPException(422, "This person is excluded from analysis.")
    elif payload.subject_id:
        raise HTTPException(422, f"{payload.kind.title()} does not accept a subject.")

    if payload.date_from and payload.date_to and payload.date_from > payload.date_to:
        raise HTTPException(422, "Start date must be before end date.")
    if payload.kind == "weekly":
        if payload.date_from is None and payload.date_to is None:
            period_end = date.today()
            data["date_from"] = str(period_end - timedelta(days=6))
            data["date_to"] = str(period_end)
        elif payload.date_from is None or payload.date_to is None:
            raise HTTPException(422, "Weekly letters require both dates.")
        elif payload.date_to - payload.date_from != timedelta(days=6):
            raise HTTPException(422, "Weekly letters cover exactly seven days.")
    return data


@router.post("/runs", status_code=202)
async def create_run(request: Request, payload: RunCreate):
    data = _effective_run_payload(_store(request), payload)
    job = request.app.state.runner.enqueue("insight", data, payload.provider)
    return {key: value for key, value in job.items() if key != "payload"}


@router.get("/runs")
def list_runs(
    request: Request,
    kind: RunKind | None = Query(default=None),
    subject_id: str | None = Query(default=None),
):
    return _store(request).list_runs(kind, subject_id)


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str):
    return _store(request).get_run(run_id)
