"""Explicit live end-to-end check in an isolated synthetic review journal."""

import asyncio

from dreamlit.config import ROOT
from dreamlit.jobs import JobRunner
from dreamlit.models import DreamCreate
from dreamlit.providers.claude import ClaudeProvider
from dreamlit.providers.codex import CodexProvider
from dreamlit.storage import Store


async def main():
    folder = ROOT / ".dreamlit" / "review-journal"
    store = Store(folder)
    if store.list_dreams():
        raise SystemExit(
            "Review journal already exists; choose a fresh review directory before rerunning."
        )
    for date, text in [
        (
            "2026-09-01",
            "I tried to call my sister from a train station. Every number I dialled disappeared. I felt desperate to explain why I was late.",
        ),
        (
            "2026-09-04",
            "At a family dinner I kept explaining that I could not stay. Everyone talked over me. I felt frustrated and invisible.",
        ),
        (
            "2026-09-09",
            "In a classroom I raised my hand to ask for help. The teacher looked through me and walked away. I felt powerless.",
        ),
    ]:
        dream = store.create_dream(DreamCreate(dreamed_on=date, text=text))
    runner = JobRunner(store, {"codex": CodexProvider(), "claude": ClaudeProvider()})
    await runner.start()
    try:
        job = runner.enqueue("analysis", {"dream_id": dream.id}, "codex")
        await runner.queue.join()
        result = store.get_job(job["id"])
        assert result["state"] == "completed", result["stage"]
        analysis = store.get_analysis(result["result_id"])
        assert analysis["patterns"], "No pattern proposed for the positive synthetic series"
        pattern = analysis["patterns"][0]
        store.add_feedback(
            pattern["id"],
            "unsure",
            "I want to distinguish a broken means of contact from another person ignoring me.",
        )
        job = runner.enqueue(
            "reflection",
            {
                "pattern_id": pattern["id"],
                "message": "Give a second opinion on this pattern and my correction.",
                "second_opinion": True,
            },
            "claude",
        )
        await runner.queue.join()
        result = store.get_job(job["id"])
        assert result["state"] == "completed", result["stage"]
        assert store.get_pattern(pattern["id"])["reflections"][0]["provider"] == "claude"
        print(
            "Live flow passed: save → Codex extraction → source-validated pattern → feedback → separate Claude second opinion.",
            flush=True,
        )
        print(f"Synthetic review data: {folder}", flush=True)
    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
