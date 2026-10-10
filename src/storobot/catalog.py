"""Catálogo permitido: os posts só podem falar destes produtos (definido pelo cliente).

Cada item tem a página do site (contexto para o Gemini), uma descrição curta em português
(para o texto), a aparência do material em inglês (para a imagem) e fotos reais do site
(assets/references/, baixadas por scripts/fetch_references.py) usadas como referência visual.
"""

from dataclasses import dataclass

SITE = "https://www.storopack.com.br/produtos/"
_COMFORT = SITE + "packaging-logistics/working-comfortr/"

_FOAM_LOOK = (
    "FOAMplus foam-in-bag cushions: soft, rounded, pillow-shaped cushions of cream/off-white expanding "
    "polyurethane foam sealed inside thin translucent plastic film bags, with irregular organic shapes that "
    "have expanded and conformed tightly around the product's contours (exactly like the reference photos)"
)


@dataclass(frozen=True)
class Product:
    name: str
    line: str
    url: str
    about_pt: str
    visual_en: str
    refs: tuple[str, ...] = ()


PRODUCTS = [
    # ---- Linha AIRplus (almofadas de ar de filme plástico) ----
    Product(
        "AIRplus Void", "AIRplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-ar/airplusr/",
        "colchões de ar para preenchimento rápido de espaços vazios e para travar e fixar o produto na caixa",
        "translucent plastic film air pillows (individual rectangular inflated cushions, connected in a strip) "
        "used as void fill around the product",
        ("airplus_void_1.jpg", "airplus_void_3.jpg"),
    ),
    Product(
        "AIRplus Cushion", "AIRplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-ar/airplusr/",
        "almofadas de ar em seções com várias câmaras, destacáveis nas perfurações, para acolchoar, travar e fixar",
        "chains of translucent plastic film air cushions, each section quilted into several small inflated chambers, "
        "placed around and under the product",
        ("airplus_cushion_1.jpg",),
    ),
    Product(
        "AIRplus Bubble", "AIRplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-ar/airplusr/",
        "filme de almofadas de ar para envolver produtos sensíveis, alternativa sob demanda ao plástico bolha",
        "translucent plastic air cushion film with rows of round inflated bubbles, wrapped around the product",
        ("airplus_wrap_1.jpg",),
    ),
    Product(
        "AIRplus Wrap (filme 28D)", "AIRplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-ar/airplusr/",
        "filme de almofadas de ar para envolver e acolchoar produtos sensíveis em toda a volta",
        "translucent plastic air cushion wrapping film made of inflated bubble chambers, wrapped around the product "
        "and lining the box",
        ("airplus_wrap_1.jpg",),
    ),
    # ---- Linha PAPERplus (papel) ----
    Product(
        "PAPERplus Classic", "PAPERplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-papel/paperplusr/paperplusr-classic/",
        "almofadas de papel robustas para acolchoar e travar, ideais para produtos pesados",
        "brown kraft paper cushioning: thick, loosely crumpled paper pads blocking and cushioning a heavy product",
        ("paperplus_classic_1.png", "paperplus_classic_2.png"),
    ),
    Product(
        "PAPERplus Shooter", "PAPERplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-papel/paperplusr/paperplusr-shooter/",
        "almofadas de papel multicamadas em altíssima velocidade (até 160 m de papel reciclado por minuto) para "
        "preencher espaços vazios",
        "brown kraft multi-layer crumpled paper cushions filling the empty space around the product in the box",
        ("paperplus_shooter_1.jpg", "paperplus_shooter_2.jpg"),
    ),
    Product(
        "PAPERplus Track", "PAPERplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-papel/paperplusr/paperplusr-track/",
        "sistema compacto de velocidade ultra-alta que produz almofadas de papel em segundos na estação de embalagem",
        "brown kraft paper pads (crumpled paper strips with a regular pleated pattern) filling voids around the product",
        ("paperplus_track_1.png", "paperplus_track_2.png"),
    ),
    Product(
        "PAPERbubble", "PAPERplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-papel/paperbubbler/",
        "folhas de papel com ar, alternativa reciclável ao filme bolha, para envolver e acolchoar produtos pequenos "
        "e médios, sem máquina",
        "sheets of brown kraft paper with an embossed honeycomb/air-pocket structure, wrapped around and between "
        "small products",
        ("paperbubble_1.png", "paperbubble_2.png"),
    ),
    # ---- Linha FOAMplus (espuma de poliuretano expansiva em saco) ----
    Product(
        "FOAMplus Bag Packer 3", "FOAMplus",
        SITE + "embalagem-de-protecao-flexivel/embalagens-de-espuma/foamplusr-bag-packer3/",
        "sistema que produz automaticamente sacos com espuma de poliuretano que se expande e se molda ao produto",
        _FOAM_LOOK,
        ("foamplus_bag_1.png", "foamplus_bag_2.png"),
    ),
    Product(
        "FOAMplus Bag Packer 2", "FOAMplus",
        SITE + "embalagem-de-protecao-flexivel/embalagens-de-espuma/",
        "sistema que produz sacos com espuma de poliuretano que se expande e se molda ao produto na caixa",
        _FOAM_LOOK,
        ("foamplus_bag_1.png", "foamplus_bag_2.png"),
    ),
    Product(
        "FOAMplus Hand Packer 2", "FOAMplus",
        SITE + "embalagem-de-protecao-flexivel/embalagens-de-espuma/foamplusr-hand-packer2/",
        "pistola de espuma para preencher a caixa com almofadas de espuma sob medida em segundos, ideal para "
        "produtos grandes, pesados ou de contornos complexos",
        "a large thin translucent plastic film bag lining the box, filled with cream/off-white expanding "
        "polyurethane foam sprayed from a handheld foam gun, expanding and molding around the product "
        "(exactly like the reference photos)",
        ("foamplus_hand_1.png", "foamplus_hand_2.png"),
    ),
    # ---- Linha Working Comfort (bancadas ergonômicas) ----
    Product(
        "COMFORT.PACK (bancadas ergonômicas)", "Working Comfort",
        _COMFORT + "comfortpack/",
        "estações de trabalho de embalagem compactas, modulares e ergonômicas, com tudo ao alcance",
        "a modern modular ergonomic packing workstation: height-adjustable table, overhead shelves and holders "
        "with everything within reach; on the table only ONE open box with a single type of protective material, "
        "no screens, no labels, no other packaging materials",
        ("comfort_pack_1.jpg",),
    ),
    Product(
        "COMFORT.ERECT (bancada ergonômica)", "Working Comfort",
        _COMFORT + "comforterect/",
        "módulo ergonômico para montar caixas de transporte planas com rapidez e facilidade",
        "an ergonomic box-erecting workstation (blue machine table) where flat cardboard blanks are quickly folded "
        "into shipping boxes; no protective material needed in the scene, no screens or labels",
        ("comfort_erect_1.jpg",),
    ),
    Product(
        "COMFORT.CLOSE (bancada ergonômica)", "Working Comfort",
        _COMFORT + "comfortclose/",
        "módulo ergonômico que fecha e sela as caixas com assistência mecânica após dobrar as abas",
        "an ergonomic box-closing workstation with a compact blue sealing machine taping a closed cardboard box; "
        "no screens or labels",
        ("comfort_close_1.jpg",),
    ),
    Product(
        "COMFORT.PROTECT (bancada ergonômica)", "Working Comfort",
        _COMFORT + "comfortprotect/",
        "módulo que mantém o material de proteção (papel, almofadas de ar ou espuma) sempre ao alcance na bancada",
        "an ergonomic packing workstation with a dispenser keeping ONE type of protective material within reach "
        "above the table, and one open box being filled with that same material; no screens or labels",
        ("comfort_protect_1.jpg",),
    ),
]

BY_NAME = {p.name: p for p in PRODUCTS}
NAMES = tuple(p.name for p in PRODUCTS)

# Materiais que a Storopack NÃO trabalha e nunca podem aparecer nas imagens
FORBIDDEN_MATERIALS_EN = (
    "EPE / polyethylene foam (sheets, planks, corner pieces, die-cut or CNC-cut inserts), EPS / styrofoam / "
    "polystyrene (blocks, molded trays, packing peanuts), any rigid or semi-rigid molded or cut foam insert with "
    "a cavity shaped like the product, foam trays, foam corners, foam sheets, bubble wrap rolls of other brands, "
    "packing peanuts and shredded paper"
)

# Páginas gerais usadas só como apoio (empresa e sustentabilidade)
SUPPORT_PAGES = [
    "https://www.storopack.com.br/empresa/sobre-nos/",
    "https://www.storopack.com.br/sustentabilidade/nossa-abordagem-de-sustentabilidade/",
]


def catalog_text() -> str:
    lines = []
    for line in dict.fromkeys(p.line for p in PRODUCTS):
        lines.append(f"Linha {line}:")
        lines += [f"  - {p.name}: {p.about_pt}" for p in PRODUCTS if p.line == line]
    return "\n".join(lines)
