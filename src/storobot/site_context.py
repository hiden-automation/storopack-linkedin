"""Raspa storopack.com.br e monta um resumo em texto usado como contexto para o Gemini."""

import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from . import config

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; storobot/1.0)"}
INCLUDE_PREFIXES = (
    "/produtos/",
    "/aplicacoes/",
    "/sustentabilidade/",
    "/empresa/sobre-nos/",
    "/empresa/processo-storopack/",
)
MAX_PAGES = 45
MAX_CHARS_PER_PAGE = 2500


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


def _internal_links(soup: BeautifulSoup) -> list[str]:
    links = []
    for a in soup.find_all("a", href=True):
        url = urljoin(config.SITE_URL + "/", a["href"])
        parsed = urlparse(url)
        if parsed.netloc != urlparse(config.SITE_URL).netloc:
            continue
        if parsed.path.startswith(INCLUDE_PREFIXES) and parsed.path not in links:
            links.append(parsed.path)
    return links


def build_site_context() -> str:
    home = _fetch(config.SITE_URL + "/")
    if home is None:
        raise RuntimeError("não foi possível acessar o site da Storopack")

    sections = [f"## Página inicial\n{_page_text(home)[:MAX_CHARS_PER_PAGE]}"]
    # Páginas mais rasas primeiro (categorias antes de produtos específicos)
    paths = sorted(_internal_links(home), key=lambda p: (p.count("/"), p))[:MAX_PAGES]
    for path in paths:
        soup = _fetch(config.SITE_URL + path)
        if soup is None:
            continue
        title = soup.title.get_text(strip=True) if soup.title else path
        text = _page_text(soup)[:MAX_CHARS_PER_PAGE]
        if len(text) > 200:
            sections.append(f"## {title}\nURL: {config.SITE_URL}{path}\n{text}")
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
