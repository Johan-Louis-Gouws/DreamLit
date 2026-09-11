"""Context voice notes stay separate from dream entries and user answers."""

from fastapi import APIRouter, Request, UploadFile

from ..audio import save_recording, transcribe_recording
from ..storage import now, uid

router = APIRouter(prefix="/api/insights/voice", tags=["insight voice"])


def note(store, note_id):
    with store.connect() as db:
        row = db.execute("SELECT * FROM insight_voice WHERE id=?", (note_id,)).fetchone()
        if row is None:
            raise KeyError("Voice note not found")
        job = db.execute(
            "SELECT id FROM jobs WHERE kind='insight_transcription' AND json_extract(payload,'$.note_id')=? ORDER BY created_at DESC LIMIT 1",
            (note_id,),
        ).fetchone()
    result = dict(row)
    result["job"] = (
        {k: v for k, v in store.get_job(job["id"]).items() if k != "payload"} if job else None
    )
    return result


@router.post("", status_code=201)
async def upload(request: Request, file: UploadFile):
    store = request.app.state.store
    audio_id = await save_recording(store, file)
    note_id = uid()
    with store.connect() as db:
        db.execute("INSERT INTO insight_voice VALUES (?,?,?,?)", (note_id, audio_id, "", now()))
    return note(store, note_id)


@router.get("")
def list_notes(request: Request):
    store = request.app.state.store
    with store.connect() as db:
        rows = db.execute(
            "SELECT id FROM insight_voice ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return [note(store, row["id"]) for row in rows]


@router.get("/{note_id}")
def get_note(request: Request, note_id: str):
    return note(request.app.state.store, note_id)


@router.post("/{note_id}/transcribe", status_code=202)
async def transcribe(request: Request, note_id: str):
    note(request.app.state.store, note_id)
    job = request.app.state.runner.enqueue("insight_transcription", {"note_id": note_id}, None)
    return {key: value for key, value in job.items() if key != "payload"}


async def transcribe_note(store, note_id, job_id, job_dir):
    original = note(store, note_id)
    text = await transcribe_recording(store, original["audio_id"], job_id, job_dir)
    with store.connect() as db:
        if not db.execute("UPDATE insight_voice SET text=? WHERE id=?", (text, note_id)).rowcount:
            raise ValueError("This voice note was deleted during transcription.")
    return note_id
