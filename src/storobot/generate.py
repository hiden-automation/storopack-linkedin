"""Worker 1: quando a fila está acabando, gera plano (12 temas) → copy → imagem de cada post.

As imagens partem SEMPRE de uma foto real do produto (biblioteca em assets/library): a IA escolhe a
foto que combina com o post e só troca o fundo branco de estúdio por um cenário. Caixa, produto e
material de proteção continuam os da foto real, para nunca desenhar um material que não existe.
"""

import argparse
import logging
import sys
from collections import Counter
from typing import Literal

from PIL import Image
from pydantic import BaseModel, Field

from . import catalog, config, gemini, image_compose, library, notify, store
from .site_context import get_site_context

log = logging.getLogger("generate")

SYSTEM = f"""Você é estrategista de conteúdo para LinkedIn de um vendedor/consultor técnico-comercial \
da Storopack Brasil. Os posts são publicados no PERFIL PESSOAL do vendedor, não na página da empresa: \
escreva em primeira pessoa, tom profissional, próximo e consultivo, em português do Brasil.
CATÁLOGO PERMITIDO — fale SOMENTE destes produtos; nunca cite, recomende ou mostre outros produtos da \
Storopack (ex.: AIRfiber, PAPERwrap, PELASPAN, outras máquinas):
{catalog.catalog_text()}
A Storopack NÃO trabalha com EPE (espuma de polietileno), EPS/isopor nem moldes de espuma recortados: a \
espuma da Storopack é sempre a FOAMplus, espuma de poliuretano expansiva dentro de sacos, que se molda ao \
produto. Nunca sugira esses outros materiais.
Use SOMENTE fatos, números e certificações presentes no contexto do site fornecido; nunca invente dados, \
clientes, preços ou estatísticas."""

ProductName = Literal[catalog.NAMES]  # type: ignore[valid-type]


class PlanItem(BaseModel):
    product: ProductName = Field(description="Produto do catálogo permitido que é o foco do post")
    topic: str = Field(description="Assunto do post, uma frase, centrado no produto escolhido")
    angle: str = Field(description="Abordagem/gancho: dica, dor do cliente, aplicação por setor, sustentabilidade etc.")


class Plan(BaseModel):
    posts: list[PlanItem]


class Copy(BaseModel):
    title: str = Field(description="Título curto e impactante para a imagem, no máximo 8 palavras, sem hashtags nem emojis")
    caption: str = Field(description="Legenda completa do post, 800 a 1500 caracteres")
    hashtags: list[str] = Field(description="3 a 5 hashtags relevantes, sem o caractere #")


def _plan_prompt(site: str, previous_topics: list[str], n: int) -> str:
    prev = "\n".join(f"- {t}" for t in previous_topics) or "(nenhum)"
    return f"""Crie um plano editorial com exatamente {n} posts para o LinkedIn. Cada post é sobre UM produto \
do catálogo permitido (campo product). Distribua os posts entre as linhas AIRplus, PAPERplus, FOAMplus e \
Working Comfort e varie os produtos (não repita o mesmo produto mais de 2 vezes). Varie as abordagens: \
benefício do produto, dor do cliente, aplicação por setor (e-commerce, automotivo, farmacêutico, alimentos, \
maquinário), sustentabilidade, redução de custos/danos e produtividade. Não repita assuntos já usados.

Assuntos já usados:
{prev}

=== CONTEXTO DO SITE (somente produtos permitidos) ===
{site}"""


def _copy_prompt(site: str, item: dict) -> str:
    product = catalog.BY_NAME[item["product"]]
    return f"""Escreva o post de LinkedIn sobre:
Produto: {product.name} (linha {product.line}) — {product.about_pt}
Assunto: {item['topic']}
Abordagem: {item['angle']}

Regras da legenda:
- Fale do produto acima (e, se fizer sentido, de outros produtos do catálogo permitido); nenhum outro produto.
- Gancho forte na primeira linha (é o que aparece antes do "ver mais").
- Parágrafos curtos, pode usar poucos emojis com moderação e listas curtas.
- A maior parte da mensagem fica na legenda; a imagem terá apenas o título.
- Termine com uma chamada para ação convidando a conversar comigo ou comentar.
- Não inclua as hashtags na legenda (elas vão no campo próprio).

=== CONTEXTO DO SITE ===
{site}"""


# ---------------------------------------------------------------- foto real + cenário

class PhotoChoice(BaseModel):
    photo: str = Field(description="Nome do arquivo da foto escolhida (exatamente como na lista)")
    scene: str = Field(description="Em inglês: o cenário ao redor da caixa (ambiente, superfície, luz), sem pessoas, telas ou textos")


def _photo_usage(posts: list[dict]) -> Counter:
    return Counter(p.get("photo") for p in posts if p.get("photo"))


def _choose_photo(post: dict, usage: Counter) -> None:
    """A IA escolhe, entre as fotos reais do produto, a que melhor combina com o post, e descreve o cenário."""
    candidates = library.for_product(post["product"])
    if not candidates:
        raise RuntimeError(f"sem fotos na biblioteca para {post['product']}")
    lines = "\n".join(
        f"- {c['file']} | tipo: {c['kind']} | usada {usage[c['file']]}x | {c['description']}" for c in candidates
    )
    choice = gemini.generate_json(
        f"""Escolha a foto real do produto que melhor ilustra este post de LinkedIn e descreva o cenário.

Post: {post['title']} — {post['topic']}
Trecho da legenda: {(post.get('caption') or '')[:600]}

Fotos disponíveis de {post['product']}:
{lines}

Regras: prefira fotos do tipo application (material protegendo um produto na caixa) quando o post fala de \
proteção, e machine/workstation quando fala de equipamento ou bancada; entre fotos adequadas, prefira as \
menos usadas. O cenário (scene) é só o ambiente em volta da foto: por exemplo uma bancada de embalagem num \
centro de distribuição de e-commerce, uma área de expedição de peças automotivas etc., coerente com o post; \
sem pessoas, sem telas, sem textos, sem outros materiais de embalagem.""",
        PhotoChoice,
    )
    entry = library.get(choice.photo, post["product"]) or min(candidates, key=lambda c: usage[c["file"]])
    post["photo"] = entry["file"]
    post["scene"] = choice.scene
    usage[entry["file"]] += 1


def _edit_prompt(scene: str) -> str:
    return (
        "Edit this real product photo. Keep EVERYTHING in the foreground exactly as it is: the cardboard box, the "
        "product inside it, the protective packaging material and any machine or equipment must stay pixel-faithful "
        "(same shapes, wrinkles, textures, colors, prints, size, position, camera angle and perspective; do not "
        "redraw, smooth, enlarge, restyle or add anything to them). Only replace the plain white studio background "
        f"with this realistic setting: {scene}. Extend the setting naturally around the subject to fill a 4:3 frame, "
        "keep the subject centered and fully visible, add a realistic contact shadow and matching soft natural "
        "light, slightly blurred background with clean blue and white accents. Add NO people, screens, text, "
        "labels, logos or other packaging materials."
    )


class EditCheck(BaseModel):
    subject_changed: bool = Field(description="Caixa, produto ou material de proteção ficaram diferentes da foto original")
    items_added: bool = Field(description="Foram adicionados materiais de embalagem, produtos, pessoas ou telas")
    text_added: bool = Field(description="Apareceu texto, número ou logotipo que não existe na foto original")
    subject_cropped: bool = Field(description="O assunto principal ficou cortado ou parcialmente fora do quadro")
    explanation: str = Field(description="Explicação curta")


EDIT_CHECK = f"""A PRIMEIRA imagem é uma foto real e oficial de produto da Storopack (fundo branco). A SEGUNDA é \
uma edição feita por IA que deveria apenas trocar o fundo por um cenário, mantendo o resto idêntico. Compare:
- subject_changed: true se a caixa, o produto dentro dela ou o material de proteção (almofadas de ar, papel, \
espuma em saco, máquina) mudaram de formato, textura, cor, quantidade, impressões ou posição em relação à \
original. Pequenas diferenças de iluminação e sombra são aceitáveis.
- items_added: true se foram adicionados outros materiais de embalagem, produtos, pessoas ou telas \
(especialmente {catalog.FORBIDDEN_MATERIALS_EN}).
- text_added: true se aparece texto, número ou logotipo que não existe na foto original.
- subject_cropped: true se o assunto principal ficou cortado ou parcialmente fora do quadro."""

MAX_EDIT_ATTEMPTS = 3
PHOTO_ASPECT = image_compose.W / image_compose.PHOTO_H


def _fit_studio(photo: Image.Image) -> Image.Image:
    """Plano B: a foto real de estúdio, sem edição, com margem branca no formato da arte."""
    w, h = photo.size
    if w / h > PHOTO_ASPECT:
        canvas = Image.new("RGB", (w, round(w / PHOTO_ASPECT)), "white")
    else:
        canvas = Image.new("RGB", (round(h * PHOTO_ASPECT), h), "white")
    canvas.paste(photo, ((canvas.width - w) // 2, (canvas.height - h) // 2))
    return canvas


def _make_image(post: dict) -> None:
    """Monta a imagem a partir da foto real escolhida; a IA só troca o fundo e é verificada contra a original."""
    entry = library.get(post["photo"], post["product"])
    if entry is None:
        raise RuntimeError(f"foto {post.get('photo')} não está na biblioteca")
    photo = library.load(entry)
    if not entry["white_background"]:
        background = photo  # já é uma foto real com cenário (ex.: bancadas)
    else:
        background = None
        for attempt in range(1, MAX_EDIT_ATTEMPTS + 1):
            edited = gemini.generate_image(_edit_prompt(post["scene"]), aspect_ratio="4:3", references=[photo])
            check = gemini.judge_image(edited, EDIT_CHECK, EditCheck, references=[photo])
            if not (check.subject_changed or check.items_added or check.text_added or check.subject_cropped):
                background = edited
                break
            log.warning("cenário de %s reprovado (tentativa %d): %s", post["id"], attempt, check.explanation)
        if background is None:
            log.warning("usando a foto de estúdio original em %s", post["id"])
            background = _fit_studio(photo)
    rel = f"images/{post['id']}.png"
    image_compose.compose(background, post["title"], config.DOCS / rel)
    post["image_path"] = rel


def _fill_post(post: dict, site: str, usage: Counter) -> None:
    try:
        if not post.get("caption"):
            copy = gemini.generate_json(_copy_prompt(site, post), Copy, SYSTEM)
            post.update(
                title=copy.title.strip(),
                caption=copy.caption.strip(),
                hashtags=[h.lstrip("#").replace(" ", "") for h in copy.hashtags],
            )
        if not post.get("photo"):
            _choose_photo(post, usage)
        if not post.get("image_path"):
            _make_image(post)
        post["status"] = "pending"
        post["error"] = None
    except Exception as exc:
        log.exception("falha no post %s", post["id"])
        post["status"] = "failed"
        post["error"] = str(exc)[:500]


def run(force: bool = False, limit: int | None = None, retry_failed: bool = False) -> int:
    state = store.load_state()
    posts = store.load_posts()
    usage = _photo_usage(posts)

    if retry_failed:
        site = get_site_context()
        failed = [p for p in posts if p["status"] == "failed"]
        for post in failed:
            _fill_post(post, site, usage)
            store.save_posts(posts)
        log.info("reprocessados %d posts com falha", len(failed))
        fixed = sum(1 for p in failed if p["status"] == "pending")
        if fixed:
            notify.send_all("Novos posts para aprovar", f"{fixed} post(s) aguardando sua aprovação.")
        return 0

    resuming = state.get("generation_status") == "in_progress"
    accepted = sum(1 for p in posts if p["status"] == "accepted")
    awaiting = sum(1 for p in posts if p["status"] in ("pending", "generating"))
    # Reposição por demanda: poucos aceitos agendados e nada esperando aprovação → gera mais
    needed = accepted <= config.REFILL_MAX_ACCEPTED and awaiting == 0
    if not (force or resuming or needed):
        log.info("%d aceitos e %d aguardando aprovação; nada a fazer", accepted, awaiting)
        return 0

    if resuming:
        cycle = state["cycle"]
        site = get_site_context()
        log.info("retomando ciclo %d", cycle)
    else:
        cycle = state.get("cycle", 0) + 1
        site = get_site_context(refresh=True)
        previous = [p["topic"] for p in posts[-48:]]
        n = limit or config.N_POSTS
        plan = gemini.generate_json(_plan_prompt(site, previous, n), Plan, SYSTEM).posts[:n]
        created = store.iso(store.now())
        for order, item in enumerate(plan, start=1):
            posts.append(
                {
                    "id": f"{cycle:03d}-{order:02d}",
                    "cycle": cycle,
                    "order": order,
                    "product": item.product,
                    "topic": item.topic,
                    "angle": item.angle,
                    "title": None,
                    "caption": None,
                    "hashtags": [],
                    "photo": None,
                    "scene": None,
                    "image_path": None,
                    "status": "generating",
                    "created_at": created,
                    "decided_at": None,
                    "posted_at": None,
                    "linkedin_urn": None,
                    "error": None,
                }
            )
        state.update(cycle=cycle, generation_status="in_progress")
        store.save_posts(posts)
        store.save_state(state)
        log.info("plano do ciclo %d criado com %d posts", cycle, len(plan))

    for post in posts:
        if post["cycle"] == cycle and post["status"] == "generating":
            log.info("gerando %s: %s", post["id"], post["topic"])
            _fill_post(post, site, usage)
            store.save_posts(posts)

    state.update(generation_status="done", last_generation_at=store.iso(store.now()))
    store.save_state(state)
    failed = sum(1 for p in posts if p["cycle"] == cycle and p["status"] == "failed")
    ready = sum(1 for p in posts if p["cycle"] == cycle and p["status"] == "pending")
    log.info("ciclo %d concluído (%d falhas)", cycle, failed)
    if ready:
        notify.send_all("Novos posts para aprovar", f"{ready} posts novos estão aguardando sua aprovação.")
    return 1 if failed else 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="gera mesmo sem precisar repor a fila")
    parser.add_argument("--limit", type=int, help="quantidade de posts (padrão: N_POSTS)")
    parser.add_argument("--retry-failed", action="store_true", help="reprocessa posts com status failed")
    args = parser.parse_args()
    sys.exit(run(force=args.force, limit=args.limit, retry_failed=args.retry_failed))


if __name__ == "__main__":
    main()
