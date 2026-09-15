import asyncio
import sys
from pathlib import Path

import pytest
from dreamlit.jobs import JobRunner
from dreamlit.models import DreamCreate
from dreamlit.providers.process import run_process
from dreamlit.storage import Store


def test_deleted_queued_job_does_not_stop_worker(tmp_path):
    async def scenario():
        store = Store(tmp_path)
        runner = JobRunner(store, {})
        await runner.start()
        dream = store.create_dream(DreamCreate(dreamed_on="2026-09-09", text="Queued dream"))
        runner.enqueue("analysis", {"dream_id": dream.id}, "codex")
        store.delete_dream(dream.id)
        later = runner.enqueue("unknown", {}, "codex")
        try:
            await asyncio.wait_for(runner.queue.join(), 0.5)
            assert store.get_job(later["id"])["state"] == "failed"
            assert not runner.worker.done()
        finally:
            await runner.stop()

    asyncio.run(scenario())


def test_cancellation_stops_child_process_group(tmp_path):
    async def scenario():
        pid_file = tmp_path / "child.pid"
        code = "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);open(sys.argv[1],'w').write(str(p.pid));time.sleep(60)"
        task = asyncio.create_task(
            run_process([sys.executable, "-c", code, str(pid_file)], "", tmp_path, 60)
        )
        for _ in range(100):
            if pid_file.exists():
                break
            await asyncio.sleep(0.02)
        assert pid_file.exists()
        child = int(pid_file.read_text())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        stat = Path(f"/proc/{child}/stat")
        try:
            state = stat.read_text().split()[2]
        except FileNotFoundError:
            state = None  # A reaped child can disappear between existence and read.
        assert state in (None, "Z")

    asyncio.run(scenario())
