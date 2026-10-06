"""Notificações push (Web Push) para quem ativou no painel.

As inscrições ficam em data/push_subscriptions.enc, criptografadas com uma chave
derivada de VAPID_PRIVATE_KEY (o repositório é público).

Uso:
    python -m storobot.notify subscribe '<json da inscrição>'
    python -m storobot.notify send "Título" "Mensagem"
"""

import base64
import hashlib
import json
import logging
import sys

from cryptography.fernet import Fernet, InvalidToken

from . import config

log = logging.getLogger("notify")


def _fernet() -> Fernet:
    digest = hashlib.sha256(config.VAPID_PRIVATE_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def load_subscriptions() -> list[dict]:
    path = config.PUSH_SUBSCRIPTIONS_FILE
    if not path.exists():
        return []
    try:
        return json.loads(_fernet().decrypt(path.read_bytes()))
    except InvalidToken:
        log.error("não foi possível ler as inscrições (VAPID_PRIVATE_KEY mudou?)")
        return []


def save_subscriptions(subs: list[dict]) -> None:
    path = config.PUSH_SUBSCRIPTIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_fernet().encrypt(json.dumps(subs).encode()))


def _send(sub: dict, payload: dict) -> bool:
    """Envia para uma inscrição. Retorna False se a inscrição expirou."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info=sub,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=config.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": config.VAPID_SUBJECT},
            ttl=24 * 3600,
            timeout=20,
        )
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (404, 410):
            return False
        log.warning("falha ao notificar %s: %s", sub.get("endpoint", "")[:60], exc)
    return True


def send_all(title: str, body: str, url: str = "./") -> None:
    """Envia para todos os inscritos; nunca levanta erro (notificação é acessória)."""
    if not config.VAPID_PRIVATE_KEY:
        log.info("VAPID_PRIVATE_KEY ausente; notificações desativadas")
        return
    try:
        subs = load_subscriptions()
        payload = {"title": title, "body": body, "url": url}
        alive = [s for s in subs if _send(s, payload)]
        if len(alive) != len(subs):
            save_subscriptions(alive)
        log.info("notificação enviada para %d aparelho(s)", len(alive))
    except Exception:
        log.exception("erro ao enviar notificações")


def subscribe(raw: str) -> None:
    sub = json.loads(raw)
    if not sub.get("endpoint") or not sub.get("keys", {}).get("p256dh"):
        sys.exit("inscrição inválida")
    subs = [s for s in load_subscriptions() if s["endpoint"] != sub["endpoint"]]
    subs.append({"endpoint": sub["endpoint"], "keys": sub["keys"]})
    save_subscriptions(subs)
    _send(sub, {"title": "Notificações ativadas", "body": "Você será avisado sobre novos posts e publicações.", "url": "./"})
    print(f"inscrição salva ({len(subs)} aparelho(s))")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if len(sys.argv) >= 3 and sys.argv[1] == "subscribe":
        subscribe(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "send":
        send_all(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
