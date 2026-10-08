"""Junta as mudanças desta execução com as que chegaram no repositório enquanto ela rodava.

Uso nos workflows (gerar/publicar podem rodar por minutos enquanto o cliente aprova posts):
    python -m storobot.sync save    # antes do commit: guarda a versão base (do checkout) e a nossa
    python -m storobot.sync merge   # após voltar para origin/main: aplica só o que NÓS mudamos

O merge é por post (id) e por campo: se nós mudamos o campo em relação à base, vale o nosso;
senão, vale o que está no repositório. Assim um aceite feito durante a geração não se perde.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config, store

SYNC_DIR = Path(os.getenv("RUNNER_TEMP") or tempfile.gettempdir()) / "storobot-sync"
FILES = {"posts": config.POSTS_FILE, "state": config.STATE_FILE}


def _git_show(path: Path, default):
    rel = path.relative_to(config.ROOT).as_posix()
    res = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=config.ROOT, capture_output=True, text=True, encoding="utf-8")
    return json.loads(res.stdout) if res.returncode == 0 else default


def _merge_dict(base: dict, ours: dict, theirs: dict) -> dict:
    merged = dict(theirs)
    for key in set(ours) | set(base):
        if ours.get(key) != base.get(key):
            if key in ours:
                merged[key] = ours[key]
            else:
                merged.pop(key, None)
    return merged


def merge_posts(base: list[dict], ours: list[dict], theirs: list[dict]) -> list[dict]:
    b = {p["id"]: p for p in base}
    o = {p["id"]: p for p in ours}
    result = []
    for post in theirs:
        pid = post["id"]
        if pid in o:
            result.append(_merge_dict(b.get(pid, {}), o[pid], post))
        elif pid in b:
            continue  # removido por nós
        else:
            result.append(post)
    seen = {p["id"] for p in result}
    result += [p for p in ours if p["id"] not in seen and p["id"] not in b]
    return result


def save() -> None:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    for name, path in FILES.items():
        default = [] if name == "posts" else {}
        (SYNC_DIR / f"{name}.base.json").write_text(json.dumps(_git_show(path, default)), encoding="utf-8")
        (SYNC_DIR / f"{name}.ours.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def merge() -> None:
    def load(name, kind):
        return json.loads((SYNC_DIR / f"{name}.{kind}.json").read_text(encoding="utf-8"))

    store.save_posts(merge_posts(load("posts", "base"), load("posts", "ours"), store.load_posts()))
    store.save_state(_merge_dict(load("state", "base"), load("state", "ours"), store.load_state()))


if __name__ == "__main__":
    {"save": save, "merge": merge}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
