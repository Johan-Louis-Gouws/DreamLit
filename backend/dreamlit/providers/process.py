import asyncio
import os
import signal
from dataclasses import dataclass

from .base import ProviderError


@dataclass
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


async def run_process(argv, input_text, cwd, timeout_seconds=240):
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
    except FileNotFoundError as error:
        raise ProviderError(
            "missing_binary",
            "Required command is not installed or its configured path is wrong.",
        ) from error
    total = 0

    async def read(stream):
        nonlocal total
        chunks = []
        while chunk := await stream.read(16384):
            total += len(chunk)
            if total > 4 * 1024 * 1024:
                raise ProviderError("output_overflow", "The CLI returned too much output.")
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")

    async def feed():
        try:
            proc.stdin.write(input_text.encode())
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            proc.stdin.close()

    async def stop():
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(proc.wait(), 2)
        except asyncio.TimeoutError:
            pass
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await proc.wait()

    tasks = [
        asyncio.create_task(feed()),
        asyncio.create_task(read(proc.stdout)),
        asyncio.create_task(read(proc.stderr)),
    ]
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout_seconds)
        await asyncio.wait_for(proc.wait(), 2)
        return ProcessResult(proc.returncode, results[1], results[2])
    except asyncio.TimeoutError as error:
        await stop()
        raise ProviderError(
            "timeout", "Analysis timed out. Your saved dream is intact; you can retry."
        ) from error
    except BaseException:
        await stop()
        raise
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
