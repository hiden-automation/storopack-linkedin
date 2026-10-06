import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config


# Brasil não tem horário de verão desde 2019
BRT = timezone(timedelta(hours=-3))


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def load_posts() -> list[dict]:
    return _read_json(config.POSTS_FILE, [])


def save_posts(posts: list[dict]) -> None:
    _write_json(config.POSTS_FILE, posts)


def load_state() -> dict:
    return _read_json(config.STATE_FILE, {"last_generation_at": None, "last_post_at": None, "cycle": 0})


def save_state(state: dict) -> None:
    _write_json(config.STATE_FILE, state)


def days_since(value: str | None) -> float | None:
    dt = parse_iso(value)
    if dt is None:
        return None
    return (now() - dt).total_seconds() / 86400


def calendar_days_since(value: str | None) -> int | None:
    """Dias de calendário (horário de Brasília) entre a data informada e hoje."""
    dt = parse_iso(value)
    if dt is None:
        return None
    return (now().astimezone(BRT).date() - dt.astimezone(BRT).date()).days
