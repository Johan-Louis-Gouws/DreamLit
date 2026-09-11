"""Run the local API and Vite together, cleaning up both on exit."""

import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = os.environ.copy()
    env.setdefault("DREAMLIT_DATA_DIR", str(ROOT / ".dreamlit" / "journal"))
    children = []
    try:
        for command in (
            [sys.executable, "-m", "dreamlit"],
            ["npm", "--prefix", "frontend", "run", "dev"],
        ):
            children.append(subprocess.Popen(command, cwd=ROOT, env=env, start_new_session=True))
        print("DreamLit development preview: http://127.0.0.1:5173", flush=True)
        while all(child.poll() is None for child in children):
            try:
                children[0].wait(timeout=1)
            except subprocess.TimeoutExpired:
                continue
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        for child in children:
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == "__main__":
    main()
