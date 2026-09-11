import asyncio
import shutil

from pydantic import ValidationError

from .analysis.evidence import EvidenceError
from .analysis.service import AnalysisService
from .providers.base import ProviderError


class JobRunner:
    def __init__(self, store, providers):
        self.store, self.providers = store, providers
        self.queue = asyncio.Queue()
        self.active = {}
        self.worker = None

    async def start(self):
        self.store.recover_jobs()
        self.worker = asyncio.create_task(self.work())

    async def stop(self):
        for task in list(self.active.values()):
            task.cancel()
        if self.worker:
            self.worker.cancel()
            await asyncio.gather(self.worker, *self.active.values(), return_exceptions=True)

    def enqueue(self, kind, payload, provider):
        job = self.store.create_job(kind, payload, provider)
        self.queue.put_nowait(job["id"])
        return job

    def cancel(self, job_id):
        self.store.get_job(job_id)
        if job_id in self.active:
            self.active[job_id].cancel()
        self.store.set_job(job_id, state="cancelled", stage="Cancelled")
        return self.store.get_job(job_id)

    async def work(self):
        while True:
            job_id = await self.queue.get()
            try:
                try:
                    queued = self.store.get_job(job_id)
                except KeyError:
                    continue
                if queued["state"] != "queued":
                    continue
                task = asyncio.create_task(self.execute(job_id))
                self.active[job_id] = task
                try:
                    await task
                except asyncio.CancelledError:
                    if asyncio.current_task().cancelling():
                        raise
                finally:
                    self.active.pop(job_id, None)
            finally:
                self.queue.task_done()

    async def execute(self, job_id):
        job = self.store.get_job(job_id)
        folder = self.store.data_dir / "jobs" / job_id
        folder.mkdir(mode=0o700, exist_ok=True)
        self.store.set_job(job_id, state="running", stage="Starting")
        service = AnalysisService(self.store, self.providers)
        try:
            payload, provider = job["payload"], job["provider"]
            if job["kind"] == "analysis":
                result_id = await service.analyse(payload["dream_id"], provider, job_id, folder)
            elif job["kind"] == "reflection":
                result_id = await service.reflect(
                    payload["pattern_id"],
                    provider,
                    payload["message"],
                    job_id,
                    folder,
                    payload.get("second_opinion", False),
                )
            elif job["kind"] == "transcription":
                from .audio import transcribe_dream

                result_id = await transcribe_dream(self.store, payload["dream_id"], job_id, folder)
            elif job["kind"] == "scan":
                from .analysis.scan import scan_history

                result_id = await scan_history(service, payload, provider, job_id, folder)
            elif job["kind"] == "insight":
                from .insights.generation import generate_insight

                result_id = await generate_insight(
                    self.store, self.providers, payload, provider, job_id, folder
                )
            elif job["kind"] == "insight_transcription":
                from .insights.voice import transcribe_note

                result_id = await transcribe_note(self.store, payload["note_id"], job_id, folder)
            elif job["kind"] == "check":
                from .models import AnalysisOutput
                from .providers.base import ProviderRequest

                prefs = self.store.preferences()
                request = ProviderRequest(
                    "check",
                    "Return summary Ready, observations [], patterns []. Do not use tools.",
                    {},
                    AnalysisOutput.model_json_schema(),
                    getattr(prefs, provider + "_model") or None,
                )
                result = await self.providers[provider].run(request, folder)
                AnalysisOutput.model_validate(result.output)
                result_id = None
                self.store.set_job(job_id, stage="Connection verified")
            else:
                raise ValueError("Unknown job type")
            self.store.set_job(
                job_id,
                state="completed",
                stage=self.store.get_job(job_id)["stage"]
                if job["kind"] in ("scan", "check")
                else "Complete",
                result_id=result_id,
            )
        except asyncio.CancelledError:
            self.store.set_job(job_id, state="cancelled", stage="Cancelled")
            raise
        except ProviderError as error:
            self.store.set_job(job_id, state="failed", error_code=error.code, stage=error.message)
        except (EvidenceError, ValidationError):
            self.store.set_job(
                job_id,
                state="failed",
                error_code="invalid_evidence",
                stage="The response could not be verified against your dreams. Retry to request a new analysis.",
            )
        except (ValueError, KeyError) as error:
            self.store.set_job(
                job_id, state="failed", error_code="invalid_request", stage=str(error)
            )
        except Exception:
            self.store.set_job(
                job_id,
                state="failed",
                error_code="internal_error",
                stage="The job could not finish. Your saved dream is intact.",
            )
        finally:
            shutil.rmtree(folder, ignore_errors=True)
