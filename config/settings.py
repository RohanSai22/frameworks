from pathlib import Path
from dataclasses import dataclass

@dataclass
class Settings:
    ARCHIVE_DIR: Path = Path("archive")
    EVAL_DIR: Path = Path("eval")
