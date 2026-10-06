"""Obtém um access token do LinkedIn (válido por 60 dias) para o perfil pessoal.

Uso (na sua máquina, não no Actions):
    python scripts/linkedin_auth.py              # mostra os valores
    python scripts/linkedin_auth.py --set-secrets  # grava direto no GitHub via `gh`

Requer no .env: LINKEDIN_CLIENT_ID e LINKEDIN_CLIENT_SECRET, e a URL
http://localhost:8765/callback cadastrada em "Authorized redirect URLs" do app.
"""

import argparse
import os
import secrets
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PORT = 8765
REDIRECT_URI = f"http://localhost:{PORT}/callback"
SCOPES = "openid profile w_member_social"


def wait_for_code(expected_state: str) -> str:
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            result.update({k: v[0] for k, v in query.items()})
            ok = "code" in query and query.get("state", [""])[0] == expected_state
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Autorizado! Pode fechar esta aba." if ok else f"Falhou: {result}"
            self.wfile.write(f"<h2>{msg}</h2>".encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", PORT), Handler)
    while "code" not in result and "error" not in result:
        server.handle_request()
    if result.get("state") != expected_state or "code" not in result:
        sys.exit(f"Autorização falhou: {result}")
    return result["code"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set-secrets", action="store_true", help="grava os secrets no repo com o gh CLI")
    args = parser.parse_args()

    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit("Defina LINKEDIN_CLIENT_ID e LINKEDIN_CLIENT_SECRET no .env")

    state = secrets.token_urlsafe(16)
    url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "scope": SCOPES,
        }
    )
    print("Abrindo o navegador para autorizar no LinkedIn...\n", url)
    webbrowser.open(url)
    code = wait_for_code(state)

    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    expires_days = resp.json().get("expires_in", 0) / 86400

    me = requests.get(
        "https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {token}"}, timeout=30
    )
    me.raise_for_status()
    person_urn = f"urn:li:person:{me.json()['sub']}"
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print(f"\nConectado como: {me.json().get('name')}  (token expira em {expires_days:.0f} dias)")
    values = {
        "LINKEDIN_ACCESS_TOKEN": token,
        "LINKEDIN_PERSON_URN": person_urn,
    }
    if args.set_secrets:
        for name, value in values.items():
            subprocess.run(["gh", "secret", "set", name, "--body", value], check=True)
        subprocess.run(["gh", "variable", "set", "LINKEDIN_TOKEN_CREATED_AT", "--body", created_at], check=True)
        print("Secrets e variable gravados no GitHub.")
    else:
        print("\nCadastre no GitHub (Settings > Secrets and variables > Actions):")
        for name, value in values.items():
            print(f"  secret   {name} = {value}")
        print(f"  variable LINKEDIN_TOKEN_CREATED_AT = {created_at}")


if __name__ == "__main__":
    main()
