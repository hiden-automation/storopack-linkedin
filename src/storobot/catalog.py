"""Catálogo permitido: os posts só podem falar destes produtos (definido pelo cliente).

Cada item tem a página do site (contexto para o Gemini), uma descrição curta em português
(para o texto) e a aparência do material em inglês (para a imagem).
"""

from dataclasses import dataclass

SITE = "https://www.storopack.com.br/produtos/"


@dataclass(frozen=True)
class Product:
    name: str
    line: str
    url: str
    about_pt: str
    visual_en: str


PRODUCTS = [
    # ---- Linha AIRplus (almofadas de ar de filme plástico) ----
    Product(
        "AIRplus Void", "AIRplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-ar/airplusr/",
        "colchões de ar para preenchimento rápido de espaços vazios e para travar e fixar o produto na caixa",
        "translucent plastic film air pillows (rectangular inflated cushions) used as void fill around the product",
    ),
    Product(
        "AIRplus Cushion", "AIRplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-ar/airplusr/",
        "almofadas de ar em seções com várias câmaras, destacáveis nas perfurações, para acolchoar, travar e fixar",
        "chains of translucent plastic film air cushions, each section quilted into several small inflated chambers, "
        "placed around and under the product",
    ),
    Product(
        "AIRplus Bubble", "AIRplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-ar/airplusr/",
        "filme de almofadas de ar para envolver produtos sensíveis, alternativa sob demanda ao plástico bolha",
        "translucent plastic air cushion film with rows of round inflated bubbles, wrapped around the product",
    ),
    Product(
        "AIRplus Wrap (filme 28D)", "AIRplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-ar/airplusr/",
        "filme de almofadas de ar para envolver e acolchoar produtos sensíveis em toda a volta",
        "translucent plastic air cushion wrapping film made of long parallel inflated tube chambers, wrapped "
        "around the product",
    ),
    # ---- Linha PAPERplus (papel) ----
    Product(
        "PAPERplus Classic", "PAPERplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-papel/paperplusr/paperplusr-classic/",
        "almofadas de papel robustas para acolchoar e travar, ideais para produtos pesados",
        "dense folded paper cushioning pads (thick crumpled paper strands) blocking and cushioning a heavy product",
    ),
    Product(
        "PAPERplus Shooter", "PAPERplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-papel/paperplusr/paperplusr-shooter/",
        "almofadas de papel multicamadas em altíssima velocidade (até 160 m de papel reciclado por minuto) para "
        "preencher espaços vazios",
        "loose crumpled multi-layer paper cushions filling the empty space in the box",
    ),
    Product(
        "PAPERplus Track", "PAPERplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-papel/paperplusr/paperplusr-track/",
        "sistema compacto de velocidade ultra-alta que produz almofadas de papel em segundos na estação de embalagem",
        "uniform crumpled paper pads produced at high speed, filling voids in the box",
    ),
    Product(
        "PAPERbubble", "PAPERplus",
        SITE + "embalagem-de-protecao-flexivel/almofadas-de-papel/paperbubbler/",
        "folhas de papel com ar, alternativa reciclável ao filme bolha, para envolver e acolchoar produtos pequenos "
        "e médios, sem máquina",
        "sheets of paper cushioning wrap with an embossed air-pocket (bubble-like) paper structure, wrapped around "
        "a small product",
    ),
    # ---- Linha FOAMplus (espuma de poliuretano) ----
    Product(
        "FOAMplus Bag Packer 3", "FOAMplus",
        SITE + "embalagem-de-protecao-flexivel/embalagens-de-espuma/foamplusr-bag-packer3/",
        "sistema que produz automaticamente sacos com espuma que se expande e se molda ao produto na caixa",
        "plastic film bags filled with expanding polyurethane foam, molded tightly around the product inside the box",
    ),
    Product(
        "FOAMplus Bag Packer 2", "FOAMplus",
        SITE + "embalagem-de-protecao-flexivel/embalagens-de-espuma/",
        "sistema que produz sacos com espuma que se expande e se molda ao produto na caixa",
        "plastic film bags filled with expanding polyurethane foam, molded tightly around the product inside the box",
    ),
    Product(
        "FOAMplus Hand Packer 2", "FOAMplus",
        SITE + "embalagem-de-protecao-flexivel/embalagens-de-espuma/foamplusr-hand-packer2/",
        "pistola de espuma para preencher a caixa com almofadas de espuma sob medida em segundos, ideal para "
        "produtos grandes, pesados ou de contornos complexos",
        "expanding polyurethane foam cushions in plastic film bags, custom-molded around a large or irregular product",
    ),
    # ---- Linha COMFORT (bancadas ergonômicas) ----
    Product(
        "COMFORT.PACK (bancadas ergonômicas)", "Working Comfort",
        SITE + "packaging-logistics/working-comfortr/comfortpack/",
        "estações de trabalho de embalagem compactas, modulares e ergonômicas, com tudo ao alcance",
        "a modern modular ergonomic packing workstation: height-adjustable table, overhead shelves and holders "
        "with everything within reach; on the table only ONE open box with a single type of protective material, "
        "no screens, no labels, no other packaging materials",
    ),
]

_COMFORT = SITE + "packaging-logistics/working-comfortr/"
PRODUCTS += [
    Product(
        "COMFORT.ERECT (bancada ergonômica)", "Working Comfort",
        _COMFORT + "comforterect/",
        "módulo ergonômico para montar caixas de transporte planas com rapidez e facilidade",
        "an ergonomic box-erecting workstation where flat cardboard blanks are quickly folded into shipping boxes; "
        "no protective material needed in the scene, no screens or labels",
    ),
    Product(
        "COMFORT.CLOSE (bancada ergonômica)", "Working Comfort",
        _COMFORT + "comfortclose/",
        "módulo ergonômico que fecha e sela as caixas com assistência mecânica após dobrar as abas",
        "an ergonomic box-closing workstation with a compact sealing machine taping a closed cardboard box; "
        "no screens or labels",
    ),
    Product(
        "COMFORT.PROTECT (bancada ergonômica)", "Working Comfort",
        _COMFORT + "comfortprotect/",
        "módulo que mantém o material de proteção (papel, almofadas de ar ou espuma) sempre ao alcance na bancada",
        "an ergonomic packing workstation with a dispenser keeping ONE type of protective material within reach "
        "above the table, and one open box being filled with that same material; no screens or labels",
    ),
]

BY_NAME = {p.name: p for p in PRODUCTS}
NAMES = tuple(p.name for p in PRODUCTS)

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
