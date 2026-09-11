import asyncio
from contextlib import asynccontextmanager
from datetime import date
from urllib.parse import urlparse

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .audio import audio_record, save_audio, transcription_status
from .config import Settings
from .export import export_journal
from .graph import build_graph
from .insights.api import router as insights_router
from .insights.voice import router as insight_voice_router
from .jobs import JobRunner
from .models import (
    AnalyseRequest,
    AssociationRequest,
    DreamCreate,
    DreamUpdate,
    ExportRequest,
    FeedbackRequest,
    Preferences,
    ReflectionRequest,
    ScanRequest,
    TranscriptAcceptance,
)
from .providers.claude import ClaudeProvider
from .providers.codex import CodexProvider
from .storage import Conflict, Store, uid


def public_job(job):
    return {k: v for k, v in job.items() if k != "payload"}


def create_app(settings=None):
    settings = settings or Settings()
    store = Store(settings.data_dir)

    @asynccontextmanager
    async def lifespan(app):
        app.state.runner = JobRunner(store, app.state.providers)
        await app.state.runner.start()
        try:
            yield
        finally:
            await app.state.runner.stop()

    app = FastAPI(title="DreamLit", lifespan=lifespan)
    app.state.store = store
    app.state.settings = settings
    app.state.providers = {
        "codex": CodexProvider(settings.cli_timeout),
        "claude": ClaudeProvider(settings.cli_timeout),
    }
    app.include_router(insights_router)
    app.include_router(insight_voice_router)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.url.hostname not in ("127.0.0.1", "localhost", "::1"):
            return JSONResponse(
                {"detail": "This app accepts local requests only."}, status_code=403
            )
        origin = request.headers.get("origin")
        if origin:
            parsed = urlparse(origin)
            allowed = {
                f"http://127.0.0.1:{settings.port}",
                f"http://localhost:{settings.port}",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            }
            if origin not in allowed or parsed.scheme != "http":
                return JSONResponse({"detail": "Origin not allowed."}, status_code=403)
        return await call_next(request)

    @app.exception_handler(KeyError)
    async def missing(request, error):
        return JSONResponse({"detail": str(error).strip("'")}, status_code=404)

    @app.exception_handler(Conflict)
    async def conflict(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/dreams", status_code=201)
    def create(data: DreamCreate):
        return store.create_dream(data)

    @app.get("/api/dreams")
    def dreams(q: str = ""):
        return store.list_dreams(q)

    @app.get("/api/dreams/{dream_id}")
    def dream(dream_id: str):
        return store.get_dream(dream_id)

    @app.get("/api/dreams/{dream_id}/revisions/{revision}")
    def revision(dream_id: str, revision: int):
        return store.get_revision(dream_id, revision)

    @app.put("/api/dreams/{dream_id}")
    def update(dream_id: str, data: DreamUpdate):
        return store.revise_dream(
            dream_id,
            data.expected_revision,
            DreamCreate(**data.model_dump(exclude={"expected_revision"})),
        )

    @app.post("/api/dreams/{dream_id}/analyse", status_code=202)
    async def analyse(dream_id: str, data: AnalyseRequest):
        dream = store.get_dream(dream_id)
        if not dream.text.strip():
            raise HTTPException(422, "Review a transcript or write your dream first.")
        return public_job(
            app.state.runner.enqueue(
                "analysis",
                {"dream_id": dream_id, "revision": dream.revision},
                data.provider,
            )
        )

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return public_job(store.get_job(job_id))

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel(job_id: str):
        return public_job(app.state.runner.cancel(job_id))

    @app.post("/api/jobs/{job_id}/retry", status_code=202)
    async def retry(job_id: str, data: AnalyseRequest):
        old = store.get_job(job_id)
        if old["state"] not in ("failed", "cancelled"):
            raise HTTPException(409, "Only failed or cancelled jobs can be retried.")
        payload = old["payload"]
        if "dream_id" in payload:
            payload["revision"] = store.get_dream(payload["dream_id"]).revision
        return public_job(
            app.state.runner.enqueue(
                old["kind"],
                payload,
                None
                if old["kind"] in ("transcription", "insight_transcription")
                else data.provider,
            )
        )

    @app.get("/api/dreams/{dream_id}/analyses")
    def analyses(dream_id: str):
        return store.list_analyses(dream_id)

    @app.get("/api/dreams/{dream_id}/activity")
    def activity(dream_id: str):
        dream = store.get_dream(dream_id)
        with store.connect() as db:
            job = db.execute(
                "SELECT id FROM jobs WHERE json_extract(payload,'$.dream_id')=? ORDER BY created_at DESC LIMIT 1",
                (dream_id,),
            ).fetchone()
            transcript = db.execute(
                "SELECT * FROM transcripts WHERE dream_id=? AND source_revision=? ORDER BY created_at DESC LIMIT 1",
                (dream_id, dream.revision),
            ).fetchone()
        return {
            "job": public_job(store.get_job(job[0])) if job else None,
            "transcript": dict(transcript) if transcript else None,
        }

    @app.get("/api/analyses/{analysis_id}")
    def analysis(analysis_id: str):
        return store.get_analysis(analysis_id)

    @app.get("/api/graph")
    def graph(
        date_from: str | None = None,
        date_to: str | None = None,
        kind: str | None = None,
    ):
        return build_graph(store, date_from, date_to, kind)

    @app.get("/api/patterns/{pattern_id}")
    def pattern(pattern_id: str):
        return store.get_pattern(pattern_id)

    @app.post("/api/patterns/{pattern_id}/feedback")
    def feedback(pattern_id: str, data: FeedbackRequest):
        store.get_pattern(pattern_id)
        return store.add_feedback(pattern_id, data.verdict, data.note)

    @app.post("/api/patterns/{pattern_id}/reflect", status_code=202)
    async def reflect(pattern_id: str, data: ReflectionRequest):
        store.get_pattern(pattern_id)
        return public_job(
            app.state.runner.enqueue(
                "reflection",
                {"pattern_id": pattern_id, "message": data.message},
                data.provider,
            )
        )

    @app.post("/api/patterns/{pattern_id}/second-opinion", status_code=202)
    async def second_opinion(pattern_id: str, data: AnalyseRequest):
        store.get_pattern(pattern_id)
        return public_job(
            app.state.runner.enqueue(
                "reflection",
                {
                    "pattern_id": pattern_id,
                    "message": "Give a second opinion on this pattern. Check alternatives and unsupported interpretations.",
                    "second_opinion": True,
                },
                data.provider,
            )
        )

    @app.get("/api/settings")
    def preferences():
        return store.preferences()

    @app.put("/api/settings")
    def preferences_update(data: Preferences):
        return store.save_preferences(data)

    @app.get("/api/providers")
    async def providers():
        return {name: await provider.preflight() for name, provider in app.state.providers.items()}

    @app.post("/api/providers/{provider}/check", status_code=202)
    async def check_provider(provider: str):
        if provider not in ("codex", "claude"):
            raise HTTPException(404, "Provider not found")
        return public_job(app.state.runner.enqueue("check", {}, provider))

    @app.get("/api/associations")
    def associations():
        return store.list_associations()

    @app.post("/api/associations", status_code=201)
    def association(data: AssociationRequest):
        if data.dream_id:
            store.get_dream(data.dream_id)
        return store.add_association(data.label, data.meaning, data.dream_id)

    @app.put("/api/associations/{association_id}")
    def update_association(association_id: str, data: AssociationRequest):
        if data.dream_id:
            store.get_dream(data.dream_id)
        with store.connect() as db:
            if not db.execute(
                "UPDATE associations SET label=?,meaning=?,dream_id=? WHERE id=?",
                (data.label, data.meaning, data.dream_id, association_id),
            ).rowcount:
                raise KeyError("Association not found")
        return {"id": association_id, **data.model_dump()}

    @app.delete("/api/associations/{association_id}")
    def delete_association(association_id: str):
        with store.connect() as db:
            db.execute("DELETE FROM associations WHERE id=?", (association_id,))
        return {"deleted": True}

    @app.delete("/api/dreams/{dream_id}")
    async def delete_dream(dream_id: str, delete_audio: bool = True):
        affected_patterns = {p["id"] for a in store.list_analyses(dream_id) for p in a["patterns"]}
        cancelled = []
        for job_id, task in list(app.state.runner.active.items()):
            job = store.get_job(job_id)
            if (
                job["kind"] == "scan"
                or job["payload"].get("dream_id") == dream_id
                or job["payload"].get("pattern_id") in affected_patterns
            ):
                app.state.runner.cancel(job_id)
                cancelled.append(task)
        await asyncio.gather(*cancelled, return_exceptions=True)
        store.delete_dream(dream_id, delete_audio)
        return {"deleted": True}

    @app.post("/api/audio", status_code=201)
    async def upload_audio(file: UploadFile, dreamed_on: date = Form(...)):
        return await save_audio(store, file, dreamed_on)

    @app.get("/api/audio/{audio_id}")
    def recording(audio_id: str):
        row = audio_record(store, audio_id)
        return FileResponse(store.data_dir / "audio" / row["filename"], media_type=row["mime_type"])

    @app.get("/api/transcription")
    def transcription():
        return transcription_status(store)

    @app.post("/api/dreams/{dream_id}/transcribe", status_code=202)
    async def transcribe(dream_id: str):
        dream = store.get_dream(dream_id)
        if not dream.audio_id:
            raise HTTPException(422, "This dream has no recording.")
        return public_job(
            app.state.runner.enqueue(
                "transcription",
                {"dream_id": dream_id, "revision": dream.revision},
                None,
            )
        )

    @app.get("/api/transcripts/{transcript_id}")
    def transcript(transcript_id: str):
        with store.connect() as db:
            row = db.execute("SELECT * FROM transcripts WHERE id=?", (transcript_id,)).fetchone()
        if not row:
            raise KeyError("Transcript not found")
        return dict(row)

    @app.post("/api/dreams/{dream_id}/accept-transcript")
    def accept_transcript(dream_id: str, data: TranscriptAcceptance):
        row = transcript(data.transcript_id)
        if row["dream_id"] != dream_id:
            raise HTTPException(422, "Transcript belongs to a different entry.")
        dream = store.get_dream(dream_id)
        return store.revise_dream(
            dream_id,
            row["source_revision"],
            DreamCreate(
                dreamed_on=dream.dreamed_on,
                text=data.text,
                context=dream.context,
            ),
        )

    @app.post("/api/export")
    def export(data: ExportRequest):
        path = store.data_dir / "exports" / (uid() + ".zip")
        export_journal(store, path, data.include_audio)
        from starlette.background import BackgroundTask

        return FileResponse(
            path,
            media_type="application/zip",
            filename="dreamlit-journal.zip",
            background=BackgroundTask(path.unlink, missing_ok=True),
        )

    @app.post("/api/scan", status_code=202)
    async def scan(data: ScanRequest):
        if data.date_from and data.date_to and data.date_from > data.date_to:
            raise HTTPException(422, "Start date must be before end date.")
        return public_job(
            app.state.runner.enqueue(
                "scan",
                data.model_dump(mode="json", exclude={"provider"}),
                data.provider,
            )
        )

    if settings.frontend_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=settings.frontend_dir, html=True),
            name="frontend",
        )
    return app
