"""Baixa as páginas dos produtos permitidos em storopack.com.br e monta o contexto do Gemini."""

import logging
import requests
from bs4 import BeautifulSoup

from . import catalog, config

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; storobot/1.0)"}
MAX_CHARS_PER_PAGE_CATALOG = 6000


def _fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("falha ao baixar %s: %s", url, exc)
        return None
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "html.parser")


def _page_text(soup: BeautifulSoup) -> str:
    main = soup.find("main") or soup.body
    if main is None:
        return ""
    for tag in main(["script", "style", "nav", "header", "footer", "noscript", "form", "video"]):
        tag.decompose()
    text = " ".join(main.get_text(" ").split())
    return text.replace("Your browser does not support the video tag.", "").replace("►", "").strip()


def build_site_context() -> str:
    """Só as páginas dos produtos do catálogo permitido, mais páginas de apoio (empresa/sustentabilidade)."""
    urls = list(dict.fromkeys([p.url for p in catalog.PRODUCTS] + catalog.SUPPORT_PAGES))
    sections = []
    for url in urls:
        soup = _fetch(url)
        if soup is None:
            continue
        title = soup.title.get_text(strip=True) if soup.title else url
        text = _page_text(soup)[:MAX_CHARS_PER_PAGE_CATALOG]
        if len(text) > 200:
            sections.append(f"## {title}\nURL: {url}\n{text}")
    if not sections:
        raise RuntimeError("não foi possível acessar o site da Storopack")
    log.info("contexto do site: %d páginas", len(sections))
    return "\n\n".join(sections)


def get_site_context(refresh: bool = False) -> str:
    path = config.SITE_CONTEXT_FILE
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    try:
        text = build_site_context()
    except RuntimeError:
        if path.exists():
            log.warning("usando contexto do site em cache")
            return path.read_text(encoding="utf-8")
        raise
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return text
