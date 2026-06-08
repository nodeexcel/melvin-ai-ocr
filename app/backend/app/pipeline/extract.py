import base64
import json
from io import BytesIO

import google.generativeai as genai
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
            {"role": "user", "content": f"{prompt}\n\n<document_text>\n{text}\n</document_text>"},
        ],
        max_tokens=8000,
        temperature=0,
    )
    content = response.choices[0].message.content
    if content is None:
        return {"raw_response": None, "parse_error": True}
    return _parse_response(content.strip())


def extract_vision_gemini(google_api_key: str, image, category: str) -> dict:
    """Extract structured data from a rendered page image using Gemini Pro."""
    prompt = EXTRACTION_PROMPTS.get(category, EXTRACTION_PROMPTS["schedules"])
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=SYSTEM_PROMPT,
    )
    response = model.generate_content(
        [prompt, image],
        generation_config=genai.GenerationConfig(temperature=0, max_output_tokens=8000),
    )
    content = response.text if response.text else None
    if content is None:
        return {"raw_response": None, "parse_error": True}
    return _parse_response(content.strip())


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
    content = response.choices[0].message.content
    if content is None:
        return {"raw_response": None, "parse_error": True}
    return _parse_response(content.strip())
