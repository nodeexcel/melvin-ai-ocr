import base64
import json
from io import BytesIO

from openai import OpenAI

from app.pipeline.prompts import EXTRACTION_PROMPTS, SYSTEM_PROMPT


def _encode_image(image) -> str:
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _parse_response(content: str) -> dict:
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1].lstrip("json").strip() if len(parts) > 1 else content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_response": content, "parse_error": True}


def extract_text(client: OpenAI, text: str, category: str) -> dict:
    """Extract structured data from raw page text (no image)."""
    prompt = EXTRACTION_PROMPTS.get(category, EXTRACTION_PROMPTS["schedules"])
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{prompt}\n\nDocument text:\n{text}"},
        ],
        max_tokens=8000,
        temperature=0,
    )
    return _parse_response(response.choices[0].message.content.strip())


def extract_vision(client: OpenAI, image, category: str) -> dict:
    """Extract structured data from a rendered page image."""
    prompt = EXTRACTION_PROMPTS.get(category, EXTRACTION_PROMPTS["schedules"])
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{_encode_image(image)}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=8000,
        temperature=0,
    )
    return _parse_response(response.choices[0].message.content.strip())
