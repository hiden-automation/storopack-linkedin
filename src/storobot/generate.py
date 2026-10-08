"""Worker 1: quando a fila está acabando, gera plano (12 temas) → copy → imagem de cada post."""

import argparse
import logging
import sys

from pydantic import BaseModel, Field

from . import config, gemini, image_compose, notify, store
from .site_context import get_site_context

log = logging.getLogger("generate")

SYSTEM = """Você é estrategista de conteúdo para LinkedIn de um vendedor/consultor técnico-comercial \
da Storopack Brasil (embalagens de proteção: almofadas de ar AIRplus, almofadas de papel PAPERplus, \
espuma FOAMplus, automação de embalagem e soluções sustentáveis). Os posts são publicados no PERFIL \
PESSOAL do vendedor, não na página da empresa: escreva em primeira pessoa, tom profissional, próximo e \
consultivo, em português do Brasil. Use SOMENTE fatos, produtos, números e certificações presentes no \
contexto do site fornecido; nunca invente dados, clientes, preços ou estatísticas."""


# Regras da Storopack para as imagens (vão no prompt e na verificação automática)
PRODUCT_RULES_PT = (
    "cada caixa deve conter UM ÚNICO tipo de material de enchimento/proteção (nunca misture, por exemplo, "
    "almofadas de ar com papel, ou espuma com papel); almofadas e enchimentos de papel são SEMPRE BRANCOS, "
    "nunca papel pardo/kraft/marrom. Descreva explicitamente na cena qual é o único material e, se for papel, "
    "que é papel branco."
)
PRODUCT_RULES_EN = (
    "Every box must contain ONLY ONE type of protective filling material - never mix materials in the same "
    "box (e.g. no air cushions together with paper, no foam together with paper). Any paper cushions or paper "
    "void fill must be PURE BRIGHT WHITE paper - never brown, kraft, beige or colored paper. Cardboard boxes "
    "themselves may be regular brown corrugated cardboard."
)


class PlanItem(BaseModel):
    topic: str = Field(description="Assunto do post, uma frase")
    angle: str = Field(description="Abordagem/gancho: dica, dor do cliente, produto, sustentabilidade, case de aplicação etc.")


class Plan(BaseModel):
    posts: list[PlanItem]


class Copy(BaseModel):
    title: str = Field(description="Título curto e impactante para a imagem, no máximo 8 palavras, sem hashtags nem emojis")
    caption: str = Field(description="Legenda completa do post, 800 a 1500 caracteres")
    hashtags: list[str] = Field(description="3 a 5 hashtags relevantes, sem o caractere #")
    image_prompt: str = Field(description="Descrição em inglês de uma cena fotográfica que represente o assunto")


def _plan_prompt(site: str, previous_topics: list[str], n: int) -> str:
    prev = "\n".join(f"- {t}" for t in previous_topics) or "(nenhum)"
    return f"""Com base no site da Storopack abaixo, crie um plano editorial com exatamente {n} posts \
para os próximos dias no LinkedIn. Varie os assuntos entre: produtos específicos, aplicações por setor \
(e-commerce, automotivo, farmacêutico, alimentos, maquinário), sustentabilidade e reciclagem, redução de \
custos/danos no transporte, automação de embalagem e dicas práticas de embalagem. Não repita assuntos já \
usados recentemente.

Assuntos já usados:
{prev}

=== CONTEXTO DO SITE ===
{site}"""


def _copy_prompt(site: str, item: dict) -> str:
    return f"""Escreva o post de LinkedIn sobre:
Assunto: {item['topic']}
Abordagem: {item['angle']}

Regras da legenda:
- Gancho forte na primeira linha (é o que aparece antes do "ver mais").
- Parágrafos curtos, pode usar poucos emojis com moderação e listas curtas.
- A maior parte da mensagem fica na legenda; a imagem terá apenas o título.
- Termine com uma chamada para ação convidando a conversar comigo ou comentar.
- Não inclua as hashtags na legenda (elas vão no campo próprio).

Regras do image_prompt: cena realista e profissional relacionada ao assunto (ex.: centro de \
distribuição, produto sendo protegido dentro de caixa, linha de embalagem), sem pessoas em close, \
SEM nenhum texto, letra, número, logotipo ou marca visível.
REGRAS DE PRODUTO (obrigatórias): {PRODUCT_RULES_PT}

=== CONTEXTO DO SITE ===
{site}"""


def _image_prompt(scene: str) -> str:
    return (
        f"{scene}. Professional high-quality commercial photograph, clean modern industrial and logistics "
        "aesthetic, soft natural lighting, shallow depth of field, color palette dominated by corporate blue "
        "(#0054A3) and white tones. Absolutely no text, no letters, no numbers, no logos, no brand names, "
        f"no watermarks, no labels on boxes. STRICT PRODUCT RULES: {PRODUCT_RULES_EN}"
    )


class ImageCheck(BaseModel):
    mixed_fillings: bool = Field(description="Alguma caixa tem mais de um tipo de material de enchimento misturado")
    non_white_paper_cushions: bool = Field(description="Há almofada/enchimento de papel que não é branco")
    text_or_logo: bool = Field(description="Há texto legível, letras, números ou logotipos")
    explanation: str = Field(description="Explicação curta do que foi observado")


CHECK_QUESTION = """Você é um revisor de imagens de uma fabricante de embalagens de proteção. Analise com \
atenção TODAS as caixas visíveis e responda:
- mixed_fillings: true se qualquer caixa contém mais de um tipo de material de enchimento ao mesmo tempo \
(ex.: almofadas de ar junto com papel, espuma junto com papel, plástico bolha junto com papel).
- non_white_paper_cushions: true se existe qualquer almofada ou enchimento de papel que NÃO seja branco \
(papel pardo, kraft, marrom, bege, colorido).
- text_or_logo: true se há texto legível, letras, números ou logotipos.
Caixas de papelão pardo são normais e não contam como enchimento."""

MAX_IMAGE_ATTEMPTS = 3


def _make_image(post: dict) -> None:
    """Gera a ilustração e só aceita se passar na verificação das regras de produto."""
    problems = ""
    for attempt in range(1, MAX_IMAGE_ATTEMPTS + 1):
        background = gemini.generate_image(_image_prompt(post["image_prompt"]))
        check = gemini.judge_image(background, CHECK_QUESTION, ImageCheck)
        if not (check.mixed_fillings or check.non_white_paper_cushions or check.text_or_logo):
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
