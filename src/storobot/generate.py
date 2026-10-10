"""Worker 1: quando a fila está acabando, gera plano (12 temas) → copy → imagem de cada post."""

import argparse
import logging
import sys
from functools import lru_cache
from typing import Literal

from PIL import Image
from pydantic import BaseModel, Field

from . import catalog, config, gemini, image_compose, notify, store
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


# Regras da Storopack para as imagens (vão no prompt e na verificação automática)
PRODUCT_RULES_PT = (
    "(1) cada caixa deve conter UM ÚNICO tipo de material de enchimento/proteção (nunca misture, por exemplo, "
    "almofadas de ar com papel, ou espuma com papel). (2) Todo material de proteção visível (cada almofada de "
    "ar, cada papel, cada saco de espuma) tem o logotipo da Storopack impresso, pequeno e discreto. "
    "(3) Os materiais têm suas cores naturais: filme plástico translúcido, papel kraft pardo ou branco, espuma "
    "clara. Descreva explicitamente na cena qual é o único material."
)
PRODUCT_RULES_EN = (
    "(1) Every box must contain ONLY ONE type of protective material - never mix materials in the same box. "
    "(2) Every visible piece of protective material (each air cushion, each paper pad, each foam bag) carries "
    "the Storopack logo from the attached reference image, printed small and subtle in blue: exactly ONE logo "
    "per piece, placed on its flattest, most visible surface, reproduced exactly as in the reference (same 'S' "
    "emblem in a circle and the 'STOROpack' wordmark, never altered, misspelled or invented). Do not repeat the "
    "logo many times and do not print it on folds or wrinkles. (3) Materials keep their natural colors (translucent plastic film, brown kraft "
    "or white paper, light-colored foam). Cardboard boxes are plain brown corrugated cardboard without print. "
    "(4) Machines, dispensers and equipment are plain, with NO printed logo, brand name, text or labels on them, "
    "and there are NO computer screens, monitors or displays in the scene (the logo appears only on the "
    "protective material)."
)

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
    image_prompt: str = Field(description="Descrição em inglês de uma cena fotográfica que represente o assunto")


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

Regras do image_prompt: cena realista e profissional relacionada ao assunto (ex.: bancada de embalagem, \
produto sendo protegido dentro de caixa aberta, centro de distribuição), sem pessoas em close, sem texto, \
letras ou números. O material de proteção mostrado deve ser exatamente: {product.visual_en}. \
Nunca descreva EPE, isopor/EPS, blocos ou moldes de espuma recortados.
REGRAS DE PRODUTO (obrigatórias): {PRODUCT_RULES_PT}

=== CONTEXTO DO SITE ===
{site}"""


def _image_prompt(scene: str, product: catalog.Product, n_refs: int) -> str:
    return (
        "The FIRST attached image is the official Storopack logo. "
        f"The next {n_refs} attached image(s) are REAL product photos of {product.name} from storopack.com.br: use "
        "them ONLY as the visual reference for how the protective material looks (shape, texture, color, how it "
        "sits in the box) and reproduce that material faithfully; create a NEW photograph (different product "
        "being protected, different angle and setting), do not copy the reference photos. "
        f"Scene: {scene}. The protective material shown is {product.visual_en}. "
        "Professional high-quality commercial photograph, clean modern industrial and logistics aesthetic, soft "
        "natural lighting, shallow depth of field, color palette dominated by corporate blue (#0054A3) and white "
        "tones. No text, letters, numbers, labels or brands anywhere EXCEPT the Storopack logo on the protective "
        f"material. STRICT PRODUCT RULES: {PRODUCT_RULES_EN} NEVER show any of these materials, which Storopack "
        f"does not sell: {catalog.FORBIDDEN_MATERIALS_EN}."
    )


class ImageCheck(BaseModel):
    forbidden_material: bool = Field(description="Aparece EPE, isopor/EPS, ou espuma rígida recortada/moldada em bloco")
    mixed_fillings: bool = Field(description="Alguma caixa tem mais de um tipo de material de proteção misturado")
    wrong_material: bool = Field(description="O material de proteção não se parece com o das fotos reais do produto")
    materials_without_logo: bool = Field(description="Há material de proteção bem visível sem o logo da Storopack")
    logo_distorted: bool = Field(description="Algum logo impresso está deformado, ilegível ou com letras erradas")
    other_text_or_logos: bool = Field(description="Há texto, números ou logos que não sejam o logo da Storopack")
    explanation: str = Field(description="Explicação curta do que foi observado")


def _check_question(product: catalog.Product, n_refs: int) -> str:
    return f"""Você é um revisor de imagens da Storopack, fabricante de embalagens de proteção. A PRIMEIRA \
imagem é o logotipo oficial da Storopack. As {n_refs} imagens seguintes são FOTOS REAIS do produto \
{product.name} (referência do material correto). A ÚLTIMA imagem é a gerada por IA, que você deve revisar. \
Material esperado: {product.visual_en}. Responda sobre a ÚLTIMA imagem:
- forbidden_material: true se aparece qualquer material que a Storopack NÃO trabalha: {catalog.FORBIDDEN_MATERIALS_EN}. \
Atenção especial: espuma em bloco/placa branca ou cinza com cavidade recortada no formato do produto é EPE/EPS \
e deve ser reprovada; a espuma da Storopack (FOAMplus) é sempre macia, arredondada, creme, dentro de sacos de \
filme plástico, moldada organicamente ao produto.
- mixed_fillings: true se qualquer caixa contém mais de um tipo de material de proteção ao mesmo tempo.
- wrong_material: true se o material de proteção visível NÃO se parece com o das fotos reais de referência \
(formato, textura, cor). Se o produto esperado é uma bancada/estação de trabalho, compare a bancada.
- materials_without_logo: true se alguma peça de material de proteção grande, em primeiro plano e com a face \
bem visível (almofada, papel, saco de espuma) NÃO tem o logo da Storopack. Peças pequenas, ao fundo ou com a \
face escondida pelo ângulo/dobra não contam. Se não há material de proteção visível, false.
- logo_distorted: true se algum logo impresso estiver claramente deformado, com letras erradas ou que não \
pareça o da referência (emblema 'S' num círculo + 'STOROpack').
- other_text_or_logos: true se há texto legível, números ou logotipos que não sejam o da Storopack \
(pequenas marcações técnicas em relevo numa peça metálica não contam).
Caixas de papelão pardo lisas são normais."""


MAX_IMAGE_ATTEMPTS = 5


@lru_cache
def _logo_reference() -> Image.Image:
    """Logo oficial com margem branca, enviado ao Gemini como referência."""
    logo = Image.open(config.DOCS / "img" / "logo_storopack_header.png").convert("RGB")
    ref = Image.new("RGB", (logo.width + 80, logo.height + 80), "white")
    ref.paste(logo, (40, 40))
    return ref


@lru_cache
def _product_references(name: str) -> tuple[Image.Image, ...]:
    """Fotos reais do produto (assets/references), reduzidas para economizar tokens."""
    images = []
    for file in catalog.BY_NAME[name].refs:
        img = Image.open(config.ASSETS / "references" / file).convert("RGB")
        img.thumbnail((1024, 1024))
        images.append(img)
    return tuple(images)


def _make_image(post: dict) -> None:
    """Gera a ilustração com o logo e fotos reais do produto como referência; só aceita se passar na verificação."""
    product = catalog.BY_NAME[post["product"]]
    refs = [_logo_reference(), *_product_references(product.name)]
    n = len(refs) - 1
    problems = ""
    for attempt in range(1, MAX_IMAGE_ATTEMPTS + 1):
        background = gemini.generate_image(_image_prompt(post["image_prompt"], product, n), references=refs)
        check = gemini.judge_image(background, _check_question(product, n), ImageCheck, references=refs)
        if not (check.forbidden_material or check.mixed_fillings or check.wrong_material
                or check.materials_without_logo or check.logo_distorted or check.other_text_or_logos):
            break
        problems = check.explanation
        log.warning("imagem de %s reprovada (tentativa %d): %s", post["id"], attempt, problems)
    else:
        raise RuntimeError(f"imagem reprovada nas regras de produto após {MAX_IMAGE_ATTEMPTS} tentativas: {problems}")
    rel = f"images/{post['id']}.png"
    image_compose.compose(background, post["title"], config.DOCS / rel)
    post["image_path"] = rel


def _fill_post(post: dict, site: str) -> None:
    try:
        if not post.get("caption"):
            copy = gemini.generate_json(_copy_prompt(site, post), Copy, SYSTEM)
            post.update(
                title=copy.title.strip(),
                caption=copy.caption.strip(),
                hashtags=[h.lstrip("#").replace(" ", "") for h in copy.hashtags],
                image_prompt=copy.image_prompt,
            )
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

    if retry_failed:
        site = get_site_context()
        failed = [p for p in posts if p["status"] == "failed"]
        for post in failed:
            _fill_post(post, site)
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
                    "image_prompt": None,
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
            _fill_post(post, site)
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
