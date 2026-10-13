"""Monta a biblioteca de fotos reais dos produtos do catálogo (assets/library/).

Varre os sites da Storopack (BR, internacional e alemão), pega as fotos de cada produto do
catálogo permitido (mapeamento curado abaixo, pelo nome do arquivo), baixa a maior versão de
cada uma, detecta se tem fundo branco e gera uma descrição curta com o Gemini, usada para
escolher a foto de cada post.

Uso: PYTHONPATH=src python scripts/build_library.py     (rode de novo quando o site ganhar fotos)
"""

import json
import re
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from storobot import catalog, gemini  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "assets" / "library"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SITES = [
    ("https://www.storopack.com.br", "/produtos/"),
    ("https://www.storopack.com", "/products/"),
    ("https://www.storopack.de", "/produkte/"),
]
LINK_KEYWORDS = re.compile(r"airplus|paperplus|paperbubble|foamplus|bag-packer|hand-packer|comfort|air-cushion|paper|foam", re.I)

# (regex no nome normalizado da foto, produto do catálogo). A primeira regra que casar vale.
# Fotos de produtos fora do catálogo (AIRfiber, Chevron, Papillon, Coiler, EPS, auto.protect...) não entram.
RULES = [
    (r"auto\.protect|coiler|chevron|papillon|dragonfly|airfiber|eps_|epp_|premold|cover_pump|integration|souriau|thumbnail|mini_touch|airmove", None),
    (r"pp_ap_void|pp_am_void|ap_bio_hc_buehne|ap_bio_hc_product", "AIRplus Void"),
    (r"pp_ap_cushion|ap_bio_hc_16p", "AIRplus Cushion"),
    (r"pp_ap_wrap", "AIRplus Wrap (filme 28D)"),
    (r"pp_ap_bubble", "AIRplus Bubble"),
    (r"pp_pp_classic(?!_ge|_gras)|pp_pp_grass_classic2_application", "PAPERplus Classic"),
    (r"pp_pp_shooter", "PAPERplus Shooter"),
    (r"pp_pp_track|paperplus_track_swivel", "PAPERplus Track"),
    (r"pp_pb_paperbubble|paperbubble_endless", "PAPERbubble"),
    (r"pp_fp_bag_packer|pp_fp_application_motive2|^bag_packer3$", "FOAMplus Bag Packer 3"),
    (r"pp_fp_hand_packer2|^hand_packer2$", "FOAMplus Hand Packer 2"),
    (r"comfort_pack|comfort\.pack|pp_pl_wat_machine", "COMFORT.PACK (bancadas ergonômicas)"),
    (r"comfort_erect", "COMFORT.ERECT (bancada ergonômica)"),
    (r"comfort_close", "COMFORT.CLOSE (bancada ergonômica)"),
    (r"comfort\.protect", "COMFORT.PROTECT (bancada ergonômica)"),
]
# Produtos sem fotos próprias usam as de outro produto da mesma família
SHARED = {
    "AIRplus Bubble": "AIRplus Wrap (filme 28D)",
    "FOAMplus Bag Packer 2": "FOAMplus Bag Packer 3",
}


class PhotoInfo(BaseModel):
    description: str = Field(description="Descrição curta em português do que a foto mostra")
    kind: str = Field(description="application (material de proteção numa caixa), machine (máquina/equipamento), "
                                  "consumable (material sozinho, fora da caixa) ou workstation (bancada/estação)")
    usable: bool = Field(description="false se é logotipo, certificado, ícone, gráfico ou foto sem o produto")


def stem(name: str) -> str:
    name = re.sub(r"^csm_", "", name)
    name = re.sub(r"_[0-9a-f]{10}\.(png|jpe?g|webp)$", "", name, flags=re.I)
    name = re.sub(r"_(\d{3,4}x\d{3,4}(px)?|low_res|zeichenflaeche_\d+)", "", name, flags=re.I)
    return name.lower().removesuffix(".png")


def product_for(name: str) -> str | None:
    for pattern, product in RULES:
        if re.search(pattern, name):
            return product
    return None


def crawl() -> dict[str, list[str]]:
    """Retorna {stem: [urls de todas as versões]} das fotos dos produtos."""
    found: dict[str, list[str]] = {}
    for host, start in SITES:
        queue, seen = [host + start], set()
        while queue and len(seen) < 70:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
            except requests.RequestException:
                continue
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for img in soup.select("img"):
                src = img.get("data-src") or img.get("src") or ""
                if "/fileadmin/" in src and not src.endswith(".svg"):
                    full = urljoin(url, src)
                    found.setdefault(stem(src.split("/")[-1]), [])
                    if full not in found[stem(src.split("/")[-1])]:
                        found[stem(src.split("/")[-1])].append(full)
            for a in soup.select("a[href]"):
                link = urlparse(urljoin(url, a["href"]))._replace(query="", fragment="")
                if link.netloc == urlparse(host).netloc and LINK_KEYWORDS.search(link.path) and link.path.count("/") <= 7:
                    queue.append(link.geturl())
        print(f"{host}: {len(seen)} páginas", flush=True)
    return found


def best_version(urls: list[str]) -> Image.Image | None:
    """Baixa todas as versões e fica com a de maior resolução."""
    best = None
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content))
            img.load()
        except Exception:
            continue
        if best is None or img.width * img.height > best.width * best.height:
            best = img
    return best


def white_background(img: Image.Image) -> bool:
    """Fundo branco = bordas quase todas brancas (foto de estúdio); senão é uma cena real."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    border = [rgb.getpixel((x, y)) for x in range(0, w, max(1, w // 60)) for y in (2, h - 3)]
    border += [rgb.getpixel((x, y)) for y in range(0, h, max(1, h // 40)) for x in (2, w - 3)]
    white = sum(1 for p in border if min(p) > 235)
    return white / len(border) > 0.85


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    groups = crawl()
    library = []
    for key, urls in sorted(groups.items()):
        product = product_for(key)
        if product is None:
            continue
        img = best_version(urls)
        if img is None or min(img.size) < 280:
            continue
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGBA", img.size, "white")
            img = Image.alpha_composite(bg, img)
        img = img.convert("RGB")
        info = gemini.judge_image(
            img,
            f"Foto oficial do site da Storopack, do produto {product}. Descreva-a para um redator escolher fotos "
            "para posts (o que está sendo protegido, qual material, enquadramento).",
            PhotoInfo,
        )
        if not info.usable:
            print("descartada:", key, "-", info.description[:60], flush=True)
            continue
        file = f"{re.sub(r'[^a-z0-9]+', '_', key).strip('_')}.jpg"
        img.save(OUT / file, "JPEG", quality=92)
        library.append({
            "file": file,
            "product": product,
            "kind": info.kind,
            "white_background": white_background(img),
            "description": info.description,
            "source": urls[0],
        })
        print(f"ok {product:38} {info.kind:12} {file}", flush=True)
    for target, source in SHARED.items():
        library += [{**item, "product": target, "shared_from": source} for item in library if item["product"] == source]
    (OUT / "library.json").write_text(json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8")
    missing = [p.name for p in catalog.PRODUCTS if not any(i["product"] == p.name for i in library)]
    print(f"{len(library)} fotos; produtos sem foto: {missing or 'nenhum'}")


if __name__ == "__main__":
    main()
