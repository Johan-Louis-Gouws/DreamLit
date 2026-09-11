"""Start the built local app, using this checkout's private journal by default."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = os.environ.copy()
    env.setdefault("DREAMLIT_DATA_DIR", str(ROOT / ".dreamlit" / "journal"))
    if not (ROOT / "frontend" / "dist" / "index.html").exists():
        subprocess.run(["npm", "--prefix", str(ROOT / "frontend"), "run", "build"], check=True)
    print("DreamLit is opening at http://127.0.0.1:8765", flush=True)
    process = subprocess.Popen([sys.executable, "-m", "dreamlit"], cwd=ROOT, env=env)
    try:
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
