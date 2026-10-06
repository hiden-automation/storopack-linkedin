"""Altera o status de um post (chamado pelo botão Aceitar/Recusar da página)."""

import argparse
import sys

from . import store

ALLOWED = {"accepted", "rejected", "pending"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post_id")
    parser.add_argument("status", choices=sorted(ALLOWED))
    args = parser.parse_args()

    posts = store.load_posts()
    post = next((p for p in posts if p["id"] == args.post_id), None)
    if post is None:
        sys.exit(f"post {args.post_id} não encontrado")
    if post["status"] not in ALLOWED:
        sys.exit(f"post {args.post_id} está '{post['status']}' e não pode mudar de status")

    post["status"] = args.status
    post["decided_at"] = store.iso(store.now()) if args.status != "pending" else None
    store.save_posts(posts)
    print(f"{args.post_id} -> {args.status}")


if __name__ == "__main__":
    main()
