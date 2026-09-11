"""Build pinned whisper.cpp and install its English base model locally."""

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

from dreamlit.config import ROOT, Settings
from dreamlit.storage import Store

VERSION = "v1.8.3"


def download(url, path):
    temporary = path.with_suffix(".part")
    request = urllib.request.Request(url, headers={"User-Agent": "DreamLit-local-setup"})
    with (
        urllib.request.urlopen(request, timeout=120) as response,
        temporary.open("wb") as handle,
    ):
        shutil.copyfileobj(response, handle)
    temporary.replace(path)


def main():
    runtime = ROOT / ".dreamlit" / "voice"
    runtime.mkdir(parents=True, exist_ok=True)
    source = runtime / f"whisper.cpp-{VERSION[1:]}"
    binary = source / "build" / "bin" / "whisper-cli"
    cmake = Path(sys.executable).parent / "cmake"
    if not cmake.exists():
        raise SystemExit("Run uv sync first to install the build tools.")
    if not shutil.which("ffmpeg"):
        raise SystemExit("Install FFmpeg using your operating system package manager first.")
    if not binary.exists():
        archive = runtime / f"whisper-{VERSION}.tar.gz"
        if not archive.exists():
            print("Downloading whisper.cpp source…", flush=True)
            download(
                f"https://github.com/ggml-org/whisper.cpp/archive/refs/tags/{VERSION}.tar.gz",
                archive,
            )
        if not source.exists():
            with tarfile.open(archive) as tar:
                tar.extractall(runtime, filter="data")
        subprocess.run(
            [
                str(cmake),
                "-S",
                str(source),
                "-B",
                str(source / "build"),
                "-DCMAKE_BUILD_TYPE=Release",
                "-DGGML_CUDA=OFF",
                "-DWHISPER_BUILD_TESTS=OFF",
            ],
            check=True,
        )
        subprocess.run(
            [
                str(cmake),
                "--build",
                str(source / "build"),
                "--target",
                "whisper-cli",
                "-j",
                "2",
            ],
            check=True,
        )
    model = runtime / "ggml-base.en.bin"
    if not model.exists():
        print("Downloading the English speech model (about 148 MB)…", flush=True)
        download(
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
            model,
        )
    sha = hashlib.file_digest(model.open("rb"), "sha256").hexdigest()
    (runtime / "installation.json").write_text(
        json.dumps(
            {"whisper_version": VERSION, "model": model.name, "model_sha256": sha},
            indent=2,
        )
    )
    store = Store(Settings().data_dir)
    prefs = store.preferences()
    prefs.whisper_binary = str(binary)
    prefs.whisper_model = str(model)
    prefs.ffmpeg_binary = shutil.which("ffmpeg")
    store.save_preferences(prefs)
    print(f"Local transcription ready. Preferences saved in {store.data_dir}", flush=True)


if __name__ == "__main__":
    main()
