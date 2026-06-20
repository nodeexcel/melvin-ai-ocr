import json
import uuid
from collections.abc import Callable
from pathlib import Path

from openai import OpenAI
from pdf2image import convert_from_path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.pipeline.aggregate import aggregate_results, inject_hardware_counts, inject_lf_data
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
    pdf_path: str = "",
) -> list[dict]:
    """Run extraction on all relevant pages. Vision-only plan pages use Gemini; others use GPT-4o.
    Scanned schedule pages (no PDF text layer) use OCR→text instead of Vision."""
    relevant = [p for p in pages if p["category"] not in ("skip", "unknown")]
    extractions = []
    for p in relevant:
        page_num = p["page"]
        category = p["category"]
        try:
            if p["use_text"]:
                data = extract_text(client, p["text"], category)
                method = "text"
            elif category == "schedules" and not p.get("text") and pdf_path:
                # Scanned schedule page: no PDF text layer, Vision misses dense tabular data.
                # Run OCR to get raw text, then use text extraction path (same as CAD PDFs).
                from app.pipeline.ocr import extract_text_from_scanned_page
                ocr_text = extract_text_from_scanned_page(pdf_path, page_num - 1)
                if ocr_text:
                    data = extract_text(client, ocr_text, category)
                    method = "ocr_text"
                else:
                    image = images.get(page_num)
                    if image is None:
                        continue
                    data = extract_vision(client, image, category)
                    method = "vision"
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
    lf_data: dict | None = None,
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
    extractions = extract_all_pages(client, pages, images, google_api_key=google_api_key, pdf_path=pdf_path)
    errors = sum(1 for e in extractions if e["data"].get("parse_error") or e["data"].get("error"))
    on_progress("extracting", f"Extracted {len(extractions)} pages ({errors} errors)", 80)

    on_progress("aggregating", "Aggregating results...", 85)
    result = aggregate_results(extractions)
    if lf_data:
        inject_lf_data(result, lf_data)
        on_progress("aggregating", f"LF injected: {lf_data.get('grand_total_lf', 0)} ft", 88)

    # Quantity estimation — preliminary lumber/plywood counts
    try:
        from app.pipeline.quantities import estimate_quantities
        result["quantities"] = estimate_quantities(result)
    except Exception:
        result["quantities"] = {}

    on_progress("aggregating", "Aggregation complete", 90)

    return result


_OCR_LF_CATEGORIES = ("foundation",)
_OCR_HW_CATEGORIES = ("foundation", "floor_framing", "roof_framing", "wall_framing", "framing_details")


def _ocr_page_indices(pages: list[dict]) -> tuple[list[int], list[int]]:
    """Return (foundation_lf_indices, structural_hw_indices) as 0-based page indices.
    LF extraction uses FOUNDATION pages only — floor/roof framing plans carry span
    and room dimensions that match the footing-dimension pattern and inflate the
    total (LHERT: 903.8 ft broad scope vs 76.8 ft foundation-only). Hardware callout
    counting uses all structural pages."""
    lf_idx = sorted({p["page"] - 1 for p in pages if p.get("category") in _OCR_LF_CATEGORIES})
    hw_idx = sorted({p["page"] - 1 for p in pages if p.get("category") in _OCR_HW_CATEGORIES})
    return lf_idx, hw_idx


def run_ocr_passes(pdf_path: str, result: dict, on_progress: ProgressCallback | None = None) -> dict:
    """PaddleOCR passes shared by the CLI and the web app — single source of truth,
    so footing-LF scope cannot drift between the two run paths. Pass 1: footing LF
    on foundation pages only. Pass 2: hardware callout counting on all structural
    pages. Gracefully no-ops if PaddleOCR is unavailable. Mutates result in place."""
    def emit(step: str, msg: str, pct: int) -> None:
        if on_progress:
            on_progress(step, msg, pct)

    try:
        from app.pipeline.ocr import count_hardware_from_pages, extract_lf_from_pages
    except Exception as e:  # PaddleOCR/fitz not importable in this environment
        emit("ocr", f"OCR unavailable, skipped: {e}", 95)
        return result

    lf_idx, hw_idx = _ocr_page_indices(result.get("_pages", []))

    if lf_idx:
        emit("ocr", f"Extracting footing dimensions from {len(lf_idx)} foundation page(s)...", 91)
        try:
            lf_data = extract_lf_from_pages(pdf_path, lf_idx)
            if lf_data.get("grand_total_lf"):
                inject_lf_data(result, lf_data)
                emit("ocr", f"Footing LF: {lf_data['grand_total_lf']} ft", 93)
            inject_hardware_counts(result, lf_data.get("hardware_counts", {}))
        except Exception as e:
            emit("ocr", f"LF pass skipped: {e}", 93)

    if hw_idx:
        emit("ocr", f"Counting hardware callouts on {len(hw_idx)} pages...", 94)
        try:
            hw_counts = count_hardware_from_pages(pdf_path, hw_idx)
            inject_hardware_counts(result, hw_counts)
            if hw_counts:
                emit("ocr", f"Hardware: {len(hw_counts)} types from callouts", 95)
        except Exception as e:
            emit("ocr", f"Hardware pass skipped: {e}", 95)

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

        # PaddleOCR passes (shared with the CLI — single source of truth, no scope drift)
        run_ocr_passes(pdf_path, result, write_event)

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
