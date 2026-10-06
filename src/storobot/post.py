"""Worker 2: a cada 3 dias publica no LinkedIn o próximo post aceito."""

import argparse
import logging
import os
import sys

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


def outside_window() -> str | None:
    """Motivo para não publicar agora, ou None se está dentro da janela."""
    local = store.now().astimezone(store.BRT)
    if not config.POST_ON_WEEKENDS and local.weekday() >= 5:
        return "fim de semana"
    if not config.POST_WINDOW_START <= local.hour < config.POST_WINDOW_END:
        return f"fora da janela {config.POST_WINDOW_START}h–{config.POST_WINDOW_END}h ({local:%H:%M})"
    return None


def run(force: bool = False, dry_run: bool = False) -> int:
    token_warning()
    reason = outside_window()
    if not force and reason:
        log.info("%s; aguardando a próxima verificação", reason)
        return 0

    state = store.load_state()
    posts = store.load_posts()

    # Conta dias de calendário: postou dia 6 em qualquer horário → próximo no dia 9
    elapsed = store.calendar_days_since(state.get("last_post_at"))
    if not force and elapsed is not None and elapsed < config.POST_EVERY_DAYS:
        log.info("último post há %d dias (< %d); nada a fazer", elapsed, config.POST_EVERY_DAYS)
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
    parser.add_argument("--force", action="store_true", help="ignora o intervalo de 3 dias e a janela de horário")
    parser.add_argument("--dry-run", action="store_true", help="mostra o texto sem publicar")
    args = parser.parse_args()
    sys.exit(run(force=args.force, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
