import base64
import json
from io import BytesIO

import google.generativeai as genai
from openai import OpenAI

from app.pipeline.prompts import DIMENSION_PROMPTS, EXTRACTION_PROMPTS, RETRY_PROMPTS, SYSTEM_PROMPT, is_refusal


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


def extract_dimensions_gemini(google_api_key: str, image, category: str) -> dict:
    """Second-pass dimension extraction — reads LF/scale from drawing image. Returns {} on any failure."""
    prompt = DIMENSION_PROMPTS.get(category)
    if not prompt:
        return {}
    try:
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=SYSTEM_PROMPT)
        response = model.generate_content(
            [prompt, image],
            generation_config=genai.GenerationConfig(temperature=0, max_output_tokens=2000),
        )
        content = response.text.strip() if response.text else ""
        if not content or is_refusal(content):
            return {}
        result = _parse_response(content)
        return {} if result.get("parse_error") else result
    except Exception:
        return {}


def extract_vision_gemini(google_api_key: str, image, category: str) -> dict:
    """Extract structured data from a rendered page image using Gemini Pro."""
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    config = genai.GenerationConfig(temperature=0, max_output_tokens=16000)

    for attempt, prompt_dict in enumerate((EXTRACTION_PROMPTS, RETRY_PROMPTS)):
        prompt = prompt_dict.get(category, EXTRACTION_PROMPTS["schedules"])
        response = model.generate_content([prompt, image], generation_config=config)
        content = response.text if response.text else None
        if content is None:
            continue
        content = content.strip()
        if is_refusal(content) and attempt == 0:
            continue
        result = _parse_response(content)
        if not result.get("parse_error"):
            return result
        if attempt == 0:
            continue
        return result

    return {"raw_response": None, "parse_error": True}


def extract_vision(client: OpenAI, image, category: str) -> dict:
    """Extract structured data from a rendered page image."""
    b64 = _encode_image(image)

    for attempt, prompt_dict in enumerate((EXTRACTION_PROMPTS, RETRY_PROMPTS)):
        prompt = prompt_dict.get(category, EXTRACTION_PROMPTS["schedules"])
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                    ],
                },
            ],
            max_tokens=8000,
            temperature=0,
        )
        content = response.choices[0].message.content
        if content is None:
            continue
        content = content.strip()
        if is_refusal(content) and attempt == 0:
            continue
        result = _parse_response(content)
        if not result.get("parse_error"):
            return result
        if attempt == 0:
            continue
        return result

    return {"raw_response": None, "parse_error": True}
