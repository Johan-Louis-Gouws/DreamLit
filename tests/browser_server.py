"""Isolated browser-test server. Never touches the personal journal or real CLIs."""

import tempfile
from pathlib import Path

import uvicorn
from dreamlit.api import create_app
from dreamlit.config import ROOT, Settings
from test_api import FixtureProvider

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="dreamlit-browser-test-") as folder:
        app = create_app(Settings(data_dir=Path(folder), port=8766))
        app.state.providers = {"codex": FixtureProvider(), "claude": FixtureProvider()}
        voice = ROOT / ".dreamlit" / "voice"
        binaries = list(voice.glob("whisper.cpp-*/build/bin/whisper-cli"))
        if binaries:
            prefs = app.state.store.preferences()
            prefs.whisper_binary = str(binaries[0])
            prefs.whisper_model = str(voice / "ggml-base.en.bin")
            app.state.store.save_preferences(prefs)
        uvicorn.run(app, host="127.0.0.1", port=8766, log_level="warning")
