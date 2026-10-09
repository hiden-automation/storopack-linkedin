import io
import logging
import time
from typing import TypeVar

from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel

from . import config

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY não definida")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _retry(fn, attempts: int = 4):
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # erros de rede/quota/resposta inválida
            if i == attempts - 1:
                raise
            wait = 10 * 2**i
            log.warning("Gemini falhou (%s); nova tentativa em %ss", exc, wait)
            time.sleep(wait)


def generate_json(prompt: str, schema: type[T], system: str | None = None) -> T:
    def call():
        resp = client().models.generate_content(
            model=config.GEMINI_TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.9,
            ),
        )
        if resp.parsed is None:
            raise ValueError(f"resposta sem JSON válido: {resp.text[:300] if resp.text else resp}")
        return resp.parsed

    return _retry(call)


def _image_part(image: Image.Image) -> types.Part:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, "JPEG", quality=88)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def judge_image(
    image: Image.Image, question: str, schema: type[T], references: list[Image.Image] | None = None
) -> T:
    """Pede ao modelo de texto (multimodal) para avaliar uma imagem e responder em JSON.
    As imagens de referência (ex.: logo oficial) vão antes da imagem avaliada."""

    def call():
        resp = client().models.generate_content(
            model=config.GEMINI_TEXT_MODEL,
            contents=[*(_image_part(r) for r in references or []), _image_part(image), question],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=schema, temperature=0
            ),
        )
        if resp.parsed is None:
            raise ValueError("verificação da imagem sem JSON válido")
        return resp.parsed

    return _retry(call)


def generate_image(
    prompt: str, aspect_ratio: str = "4:5", references: list[Image.Image] | None = None
) -> Image.Image:
    """Gera uma imagem; `references` (ex.: o logo oficial) são enviadas junto como referência visual."""

    def call():
        resp = client().models.generate_content(
            model=config.GEMINI_IMAGE_MODEL,
            contents=[*(_image_part(r) for r in references or []), prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else None) or []:
                if part.inline_data and part.inline_data.data:
                    return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
        raise ValueError("Gemini não retornou imagem")

    return _retry(call)
