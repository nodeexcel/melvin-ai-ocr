import json
import uuid
from collections.abc import Callable
from pathlib import Path

from openai import OpenAI
from pdf2image import convert_from_path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.pipeline.aggregate import aggregate_results
from app.pipeline.classify import classify_pages
from app.pipeline.extract import extract_dimensions_gemini, extract_text, extract_vision, extract_vision_gemini

ProgressCallback = Callable[[str, str, int], None]


def render_vision_pages(pdf_path: str, pages: list[dict], dpi: int = 250) -> dict[int, object]:
    """Render vision-only pages to PIL images. Returns {page_num: image}."""
    vision_pages = [p for p in pages if not p["use_text"] and p["category"] not in ("skip", "unknown")]
    images = {}
    for p in vision_pages:
        page_num = p["page"]
        rendered = convert_from_path(pdf_path, dpi=dpi, first_page=page_num, last_page=page_num)
        images[page_num] = rendered[0]
    return images


GEMINI_CATEGORIES = {"floor_framing", "roof_framing", "foundation"}


def extract_all_pages(
    client: OpenAI,
    pages: list[dict],
    images: dict[int, object],
    google_api_key: str = "",
) -> list[dict]:
    """Run extraction on all relevant pages. Vision-only plan pages use Gemini; others use GPT-4o."""
    relevant = [p for p in pages if p["category"] not in ("skip", "unknown")]
    extractions = []
    for p in relevant:
        page_num = p["page"]
        category = p["category"]
        try:
            if p["use_text"]:
                data = extract_text(client, p["text"], category)
                method = "text"
            else:
                image = images.get(page_num)
                if image is None:
                    continue
                if google_api_key and category in GEMINI_CATEGORIES:
                    data = extract_vision_gemini(google_api_key, image, category)
                    method = "vision_gemini"
                    dim = extract_dimensions_gemini(google_api_key, image, category)
                    if dim:
                        data = {**data, **{k: v for k, v in dim.items() if v}}

                else:
                    data = extract_vision(client, image, category)
                    method = "vision"
            extractions.append({"page": page_num, "category": category, "data": data, "method": method})
        except Exception as e:
            extractions.append({
                "page": page_num,
                "category": category,
                "data": {"error": str(e)},
                "method": "error",
            })
    return extractions


def run_pipeline_sync(
    pdf_path: str,
    openai_api_key: str,
    on_progress: ProgressCallback,
    google_api_key: str = "",
) -> dict:
    """
    Run the full extraction pipeline synchronously.
    Calls on_progress(step, message, pct) after each phase.
    Returns the aggregated result dict.
    """
    client = OpenAI(api_key=openai_api_key)

    on_progress("classifying", "Analysing PDF...", 5)
    pages = classify_pages(client, pdf_path, on_progress)

    relevant_count = sum(1 for p in pages if p["category"] not in ("skip", "unknown"))
    on_progress("classifying", f"Found {relevant_count} relevant pages out of {len(pages)} total", 38)

    on_progress("rendering", "Rendering pages for visual analysis...", 43)
    images = render_vision_pages(pdf_path, pages)
    on_progress("rendering", f"Rendered {len(images)} pages", 48)

    on_progress("extracting", f"Extracting data from {relevant_count} pages...", 53)
    extractions = extract_all_pages(client, pages, images, google_api_key=google_api_key)
    errors = sum(1 for e in extractions if e["data"].get("parse_error") or e["data"].get("error"))
    on_progress("extracting", f"Extracted {len(extractions)} pages ({errors} errors)", 80)

    on_progress("aggregating", "Aggregating results...", 85)
    result = aggregate_results(extractions)
    on_progress("aggregating", "Aggregation complete", 90)

    return result


def pipeline_worker(
    project_id: str,
    pdf_path: str,
    output_dir: str,
    db_sync_url: str,
    openai_api_key: str,
    google_api_key: str = "",
) -> None:
    """
    Entry point for ProcessPoolExecutor. Runs in a separate OS process.
    Creates its own synchronous DB connection — cannot share the async engine.
    """
    engine = create_engine(db_sync_url)

    def write_event(step: str, message: str, pct: int) -> None:
        with Session(engine) as session:
            session.execute(
                text(
                    "INSERT INTO job_events (project_id, step, message, progress_pct) "
                    "VALUES (:pid, :step, :msg, :pct)"
                ),
                {"pid": project_id, "step": step, "msg": message, "pct": pct},
            )
            session.commit()

    def update_status(status: str, set_completed: bool = False) -> None:
        if set_completed:
            with Session(engine) as session:
                session.execute(
                    text("UPDATE projects SET status = :status, completed_at = CURRENT_TIMESTAMP WHERE id = :pid"),
                    {"status": status, "pid": project_id},
                )
                session.commit()
        else:
            with Session(engine) as session:
                session.execute(
                    text("UPDATE projects SET status = :status WHERE id = :pid"),
                    {"status": status, "pid": project_id},
                )
                session.commit()

    try:
        update_status("processing")
        write_event("started", "Pipeline started", 0)

        result = run_pipeline_sync(
            pdf_path=pdf_path,
            openai_api_key=openai_api_key,
            on_progress=write_event,
            google_api_key=google_api_key,
        )

        result_id = str(uuid.uuid4())
        with Session(engine) as session:
            session.execute(
                text(
                    "INSERT INTO analysis_results (id, project_id, raw_json) "
                    "VALUES (:id, :pid, CAST(:json AS jsonb))"
                ),
                {"id": result_id, "pid": project_id, "json": json.dumps(result)},
            )
            session.commit()

        write_event("done", "Analysis complete", 100)
        update_status("done", set_completed=True)

    except Exception as e:
        try:
            write_event("error", f"Pipeline failed: {e}", 0)
        except Exception:
            pass
        try:
            update_status("failed")
        except Exception:
            pass
    finally:
        engine.dispose()
