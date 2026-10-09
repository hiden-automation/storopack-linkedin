"""Worker 2: segunda, quarta e sexta, por volta das 10h, publica no LinkedIn o próximo post aceito."""

import argparse
import logging
import os
import sys
from datetime import timedelta

from . import config, linkedin, notify, store

log = logging.getLogger("post")


def full_text(post: dict) -> str:
    tags = " ".join(f"#{h}" for h in post.get("hashtags") or [])
    return f"{post['caption']}\n\n{tags}".strip()


def next_accepted(posts: list[dict]) -> dict | None:
    accepted = [p for p in posts if p["status"] == "accepted" and p.get("image_path")]
    return min(accepted, key=lambda p: (p["cycle"], p["order"]), default=None)


def token_warning() -> None:
    """Escreve aviso no arquivo apontado por TOKEN_WARNING_FILE se o token estiver perto de expirar."""
    age = store.days_since(config.LINKEDIN_TOKEN_CREATED_AT or None)
    if age is None:
        return
    remaining = config.LINKEDIN_TOKEN_TTL_DAYS - age
    log.info("token do LinkedIn expira em %.0f dias", remaining)
    target = os.getenv("TOKEN_WARNING_FILE")
    if remaining <= 7 and target:
        with open(target, "w", encoding="utf-8") as f:
            f.write(f"{max(remaining, 0):.0f}")


WEEKDAY_NAMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def missed_post_day(last_post_at: str | None) -> bool:
    """Houve algum dia de post (seg/qua/sex) depois do último post e antes de hoje sem publicação?"""
    last = store.parse_iso(last_post_at)
    if last is None:
        return False
    day = last.astimezone(store.BRT).date() + timedelta(days=1)
    today = store.now().astimezone(store.BRT).date()
    while day < today:
        if day.weekday() in config.POST_WEEKDAYS:
            return True
        day += timedelta(days=1)
    return False


def outside_window(last_post_at: str | None = None) -> str | None:
    """Motivo para não publicar agora, ou None se pode publicar."""
    local = store.now().astimezone(store.BRT)
    catch_up = local.weekday() < 5 and missed_post_day(last_post_at)
    if local.weekday() not in config.POST_WEEKDAYS and not catch_up:
        return f"{WEEKDAY_NAMES[local.weekday()]} não é dia de publicação"
    if not config.POST_WINDOW_START <= local.hour < config.POST_WINDOW_END:
        return f"fora da janela {config.POST_WINDOW_START}h–{config.POST_WINDOW_END}h ({local:%H:%M})"
    return None


def run(force: bool = False, dry_run: bool = False) -> int:
    token_warning()
    state = store.load_state()
    posts = store.load_posts()

    reason = outside_window(state.get("last_post_at"))
    if not force and reason:
        log.info("%s; aguardando a próxima verificação", reason)
        return 0

    # No máximo um post por dia
    if not force and store.calendar_days_since(state.get("last_post_at")) == 0:
        log.info("já houve publicação hoje; nada a fazer")
        return 0

    post = next_accepted(posts)
    if post is None:
        log.info("nenhum post aceito na fila")
        return 0

    log.info("publicando %s: %s", post["id"], post["title"])
    if dry_run:
        print(full_text(post))
        return 0

    try:
        asset = linkedin.upload_image(config.DOCS / post["image_path"])
        urn = linkedin.create_image_post(full_text(post), asset, post["title"])
    except Exception as exc:
        post["error"] = str(exc)[:500]
        store.save_posts(posts)
        log.error("falha ao publicar: %s", exc)
        return 1

    now = store.iso(store.now())
    post.update(status="posted", posted_at=now, linkedin_urn=urn, error=None)
    state["last_post_at"] = now
    store.save_posts(posts)
    store.save_state(state)
    log.info("publicado: %s", urn)
    notify.send_all("Post publicado no LinkedIn", post["title"])
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="ignora o dia/horário de publicação e o limite de um post por dia")
    parser.add_argument("--dry-run", action="store_true", help="mostra o texto sem publicar")
    args = parser.parse_args()
    sys.exit(run(force=args.force, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
