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

CYCLE_DAYS = int(os.getenv("CYCLE_DAYS") or 30)
POST_EVERY_DAYS = int(os.getenv("POST_EVERY_DAYS") or 3)
N_POSTS = int(os.getenv("N_POSTS") or 12)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL") or "gemini-3.8-flash"
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL") or "gemini-3.1-flash-image"

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")
LINKEDIN_TOKEN_CREATED_AT = os.getenv("LINKEDIN_TOKEN_CREATED_AT", "")
LINKEDIN_TOKEN_TTL_DAYS = 60

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT") or "https://github.com"
PUSH_SUBSCRIPTIONS_FILE = ROOT / "data" / "push_subscriptions.enc"

# Identidade visual extraída do CSS de storopack.com.br
BRAND_BLUE = "#0054A3"
BRAND_LIGHT_BLUE = "#0096DA"
BRAND_NAVY = "#162F4F"
BRAND_GRAY = "#F6F6F6"
