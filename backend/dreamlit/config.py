import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("DREAMLIT_DATA_DIR", "~/.local/share/dreamlit")
        ).expanduser()
    )
    host: str = "127.0.0.1"
    port: int = 8765
    cli_timeout: float = 240
    frontend_dir: Path = ROOT / "frontend" / "dist"
    knowledge_dir: Path = ROOT / "knowledge"

    def __post_init__(self):
        self.data_dir = Path(self.data_dir).expanduser().resolve()
