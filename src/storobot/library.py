"""Biblioteca de fotos reais dos produtos (assets/library/, montada por scripts/build_library.py)."""

import json
from functools import lru_cache

from PIL import Image

from . import config

LIBRARY_DIR = config.ASSETS / "library"


@lru_cache
def entries() -> tuple[dict, ...]:
    return tuple(json.loads((LIBRARY_DIR / "library.json").read_text(encoding="utf-8")))


def for_product(product: str) -> list[dict]:
    return [e for e in entries() if e["product"] == product]


def get(file: str, product: str | None = None) -> dict | None:
    return next((e for e in entries() if e["file"] == file and (product is None or e["product"] == product)), None)


def load(entry: dict) -> Image.Image:
    return Image.open(LIBRARY_DIR / entry["file"]).convert("RGB")
