import os
import re
from datetime import datetime
from pathlib import Path

_data_dir = Path(os.getenv("DB_PATH", "/app/data/gamie.db")).parent
JOURNAL_PATH = _data_dir / "Journal.md"


def read_journal() -> str:
    if not JOURNAL_PATH.exists():
        return ""
    return JOURNAL_PATH.read_text(encoding="utf-8")


def read_journal_summary(max_turns: int = 10) -> str:
    """Return the prologue plus the last max_turns turns only."""
    if not JOURNAL_PATH.exists():
        return ""
    content = JOURNAL_PATH.read_text(encoding="utf-8")
    sections = re.split(r"(?=### (?:Turn|Prologue))", content)
    prologue = [s for s in sections if s.startswith("### Prologue")]
    turns = [s for s in sections if s.startswith("### Turn")]
    recent = prologue + turns[-max_turns:]
    return "".join(recent).strip()


def append_journal(entry: str, turn_number: int) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = f"### Turn {turn_number} — {timestamp}\n{entry}\n---\n\n"
    if not JOURNAL_PATH.exists():
        JOURNAL_PATH.write_text(f"# Journal\n\n{block}", encoding="utf-8")
    else:
        with JOURNAL_PATH.open("a", encoding="utf-8") as f:
            f.write(block)


def init_journal(initial_hook: str) -> None:
    """Always overwrites — called when a new session starts."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    JOURNAL_PATH.write_text(
        f"# Journal\n\n### Prologue — {timestamp}\n{initial_hook}\n---\n\n",
        encoding="utf-8",
    )
