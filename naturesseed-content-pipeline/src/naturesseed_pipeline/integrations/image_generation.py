"""AI image generation and optimization.

Generates images via OpenAI Images API (or Stability if configured).
Optimizes images: WebP conversion, resize, EXIF strip.
Generates SEO-friendly alt text.
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any

import structlog

from naturesseed_pipeline.config import settings

log = structlog.get_logger()


def _load_image_style() -> str:
    """Load image style guidelines for prompt engineering."""
    path = Path("config/image_style.md")
    if path.exists():
        return path.read_text()
    return ""


def generate_image(
    description: str,
    slug: str,
    slot: str = "hero",
    size: str = "1792x1024",
) -> dict[str, Any] | None:
    """Generate an image via OpenAI DALL-E 3.

    Returns dict with local_path, prompt used, or None on failure.
    """
    if not settings.openai_api_key:
        log.warning("openai_api_key_missing")
        return None

    style_guide = _load_image_style()
    # Extract style keywords from guide
    style_additions = "natural lighting, earthy tones, photorealistic, editorial quality"

    prompt = f"{description}. Style: {style_additions}"

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt[:4000],
            size=size,
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        if not image_url:
            return None

        # Download image
        import httpx

        img_response = httpx.get(image_url)
        img_response.raise_for_status()

        # Save locally
        out_dir = Path(f"assets/generated/{slug}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{slot}.png"
        out_path.write_bytes(img_response.content)

        log.info("image_generated", path=str(out_path))
        return {
            "local_path": str(out_path),
            "prompt": prompt,
            "source": "openai_dalle3",
        }

    except Exception as e:
        log.error("image_generation_failed", error=str(e))
        return None


def optimize_image(
    input_path: str,
    output_path: str | None = None,
    max_width: int | None = None,
) -> str:
    """Optimize image: convert to WebP, resize, strip EXIF.

    Returns the output path.
    """
    from PIL import Image

    if max_width is None:
        max_width = settings.image_max_width

    img = Image.open(input_path)

    # Strip EXIF by creating a new image
    data = list(img.getdata())
    clean_img = Image.new(img.mode, img.size)
    clean_img.putdata(data)

    # Resize if too wide
    if clean_img.width > max_width:
        ratio = max_width / clean_img.width
        new_height = int(clean_img.height * ratio)
        clean_img = clean_img.resize((max_width, new_height), Image.LANCZOS)

    # Convert to WebP
    if output_path is None:
        p = Path(input_path)
        output_path = str(p.with_suffix(".webp"))

    clean_img.save(output_path, "WEBP", quality=85)
    log.info("image_optimized", input=input_path, output=output_path, width=clean_img.width)
    return output_path


def generate_alt_text(image_path: str, context: str = "") -> str:
    """Generate SEO-friendly alt text for an image.

    Uses OpenAI vision if available, otherwise generates from context.
    """
    if settings.openai_api_key:
        try:
            return _generate_alt_with_vision(image_path, context)
        except Exception as e:
            log.warning("vision_alt_failed", error=str(e))

    # Fallback: generate from context
    return _generate_alt_from_context(context)


def _generate_alt_with_vision(image_path: str, context: str) -> str:
    """Use OpenAI vision to describe an image for alt text."""
    import base64

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    mime = "image/webp" if image_path.endswith(".webp") else "image/png"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Generate a concise, SEO-friendly alt text for this image. "
                        "Context: this image is for a gardening/seed company article. "
                        f"Article context: {context[:200]}. "
                        "Rules: describe what's IN the image, include plant names if visible, "
                        "mention any action, keep under 125 characters, don't start with 'Image of'."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{image_data}"},
                },
            ],
        }],
        max_tokens=100,
    )

    alt = response.choices[0].message.content or ""
    return alt.strip()[:125]


def _generate_alt_from_context(context: str) -> str:
    """Generate alt text from context when vision is unavailable."""
    if not context:
        return "Nature's Seed gardening image"
    # Take first meaningful phrase
    words = context.split()[:12]
    return " ".join(words)[:125]
