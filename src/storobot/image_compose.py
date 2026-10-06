"""Monta a arte final: ilustração da IA + título + logo original, na identidade Storopack."""

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

from . import config

W, H = 1080, 1350
PHOTO_H = 800
FOOTER_H = 150
PANEL_TOP = PHOTO_H
PANEL_BOTTOM = H - FOOTER_H
MARGIN = 72


@lru_cache
def _logo() -> Image.Image:
    logo = Image.open(config.LOGO_FILE).convert("RGB")
    # Recorta o espaço em branco ao redor do logo, sem alterar o desenho
    diff = ImageChops.difference(logo, Image.new("RGB", logo.size, "white"))
    bbox = ImageOps.grayscale(diff).point(lambda p: 255 if p > 20 else 0).getbbox()
    return logo.crop(bbox) if bbox else logo


def _font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(config.FONT_FILE), size)
    font.set_variation_by_name(weight)
    return font


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_title(draw, text: str, max_width: int, max_height: int):
    for size in range(96, 39, -4):
        font = _font(size)
        lines = _wrap(draw, text, font, max_width)
        line_h = int(size * 1.12)
        too_wide = any(draw.textlength(line, font=font) > max_width for line in lines)
        if len(lines) <= 4 and len(lines) * line_h <= max_height and not too_wide:
            return font, lines, line_h
    font = _font(40)
    return font, _wrap(draw, text, font, max_width), 45


def _cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.5))


def compose(background: Image.Image, title: str, out_path: Path) -> Path:
    canvas = Image.new("RGB", (W, H), config.BRAND_BLUE)
    canvas.paste(_cover(background, (W, PHOTO_H)), (0, 0))

    # Degradê suave da foto para o azul da marca
    grad_h = 220
    gradient = Image.new("L", (1, grad_h))
    for y in range(grad_h):
        gradient.putpixel((0, y), int(255 * (y / grad_h) ** 2))
    gradient = gradient.resize((W, grad_h))
    canvas.paste(Image.new("RGB", (W, grad_h), config.BRAND_BLUE), (0, PHOTO_H - grad_h), gradient)

    draw = ImageDraw.Draw(canvas)

    # Título
    accent_y = PANEL_TOP + 20
    draw.rectangle([MARGIN, accent_y, MARGIN + 110, accent_y + 10], fill=config.BRAND_LIGHT_BLUE)
    title_top = accent_y + 44
    font, lines, line_h = _fit_title(draw, title, W - 2 * MARGIN, PANEL_BOTTOM - title_top - 40)
    y = title_top + (PANEL_BOTTOM - title_top - 40 - len(lines) * line_h) // 2
    for line in lines:
        draw.text((MARGIN, y), line, font=font, fill="white")
        y += line_h

    # Rodapé branco com o logo original
    draw.rectangle([0, PANEL_BOTTOM, W, H], fill="white")
    logo = _logo()
    logo_h = FOOTER_H - 56
    logo = logo.resize((int(logo.width * logo_h / logo.height), logo_h), Image.LANCZOS)
    canvas.paste(logo, (W - MARGIN - logo.width, PANEL_BOTTOM + (FOOTER_H - logo_h) // 2))
    site_font = _font(34, "SemiBold")
    draw.text(
        (MARGIN, PANEL_BOTTOM + FOOTER_H // 2),
        "storopack.com.br",
        font=site_font,
        fill=config.BRAND_NAVY,
        anchor="lm",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "PNG", optimize=True)
    return out_path
