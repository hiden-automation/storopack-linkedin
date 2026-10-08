import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
DATA_DIR = DOCS / "data"
IMAGES_DIR = DOCS / "images"
POSTS_FILE = DATA_DIR / "posts.json"
STATE_FILE = DATA_DIR / "state.json"
SITE_CONTEXT_FILE = ROOT / "cache" / "site_context.md"

ASSETS = ROOT / "assets"
LOGO_FILE = DOCS / "img" / "logo_storopack.jpg"
FONT_FILE = ASSETS / "fonts" / "SourceSans3.ttf"

SITE_URL = "https://www.storopack.com.br"

N_POSTS = int(os.getenv("N_POSTS") or 12)
# Gera mais N_POSTS quando há até esta quantidade de aceitos e nenhum aguardando aprovação
REFILL_MAX_ACCEPTED = int(os.getenv("REFILL_MAX_ACCEPTED") or 3)

# Publicação (horário de Brasília): segunda, quarta e sexta, por volta das 10h
# Dias: 0=segunda … 6=domingo. A janela cobre atrasos do agendador do GitHub.
POST_WEEKDAYS = [int(d) for d in (os.getenv("POST_WEEKDAYS") or "0,2,4").split(",")]
POST_WINDOW_START = int(os.getenv("POST_WINDOW_START") or 9)
POST_WINDOW_END = int(os.getenv("POST_WINDOW_END") or 12)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL") or "gemini-3.8-flash"
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL") or "gemini-3.1-flash-image"

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")
LINKEDIN_TOKEN_CREATED_AT = os.getenv("LINKEDIN_TOKEN_CREATED_AT", "")
LINKEDIN_TOKEN_TTL_DAYS = 60

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
# O "sub" do VAPID precisa ser mailto: ou só o domínio https (sem caminho)
_subject = os.getenv("VAPID_SUBJECT") or "https://github.com"
VAPID_SUBJECT = "/".join(_subject.split("/")[:3]) if _subject.startswith("https://") else _subject
PUSH_SUBSCRIPTIONS_FILE = ROOT / "data" / "push_subscriptions.enc"

# Identidade visual extraída do CSS de storopack.com.br
BRAND_BLUE = "#0054A3"
BRAND_LIGHT_BLUE = "#0096DA"
BRAND_NAVY = "#162F4F"
BRAND_GRAY = "#F6F6F6"
