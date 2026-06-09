#!/usr/bin/env python3
"""
Test any PDF through the production pipeline.
Uses the same code as the web app — no duplicate logic.

Usage (inside Docker):
  docker compose exec backend python scripts/test_pdf.py --pdf /path/to/plans.pdf

Usage (local):
  cd app/backend
  PYTHONPATH=. python scripts/test_pdf.py --pdf /path/to/plans.pdf
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_OCR_SCRIPT = _REPO_ROOT / "scripts" / "ocr" / "extract_lf.py"
_PY311 = _REPO_ROOT / "venv" / "melvin311" / "bin" / "python"
_OCR_CATEGORIES = {"foundation", "floor_framing", "roof_framing"}


def _run_lf_extraction(pdf_path: str, page_indices: list[int]) -> dict:
    """Try module import first (Docker/Python 3.11 venv), fall back to subprocess."""
    try:
        from app.pipeline.ocr import extract_lf_from_pages
        result = extract_lf_from_pages(pdf_path, page_indices)
        if result:
            return result
    except Exception:
        pass
    # Fallback: subprocess via Python 3.11
    if _PY311.exists() and _OCR_SCRIPT.exists():
        pages_str = ",".join(str(i + 1) for i in page_indices)
        proc = subprocess.run(
            [str(_PY311), str(_OCR_SCRIPT), "--pdf", pdf_path, "--pages", pages_str],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    return {}

# Ensure app package is importable whether running locally or inside Docker
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Load .env from app/ for local dev. In Docker, env vars are already injected.
env_file = _backend_dir.parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)

from app.pipeline.runner import run_pipeline_sync


def on_progress(step: str, message: str, pct: int) -> None:
    print(f"  [{pct:3d}%] {step}: {message}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--out", default=None, help="Output JSON path (default: scripts/output/<name>_results.json)")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set. Check app/.env", file=sys.stderr)
        sys.exit(1)

    google_api_key = os.environ.get("GOOGLE_API_KEY", "")

    pdf_path = args.pdf
    if not Path(pdf_path).exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    pdf_name = Path(pdf_path).stem.replace(" ", "_")
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_file = Path(args.out) if args.out else out_dir / f"{pdf_name}_results.json"

    print(f"\nProcessing: {Path(pdf_path).name}")
    print("=" * 60)

    t0 = time.time()
    result = run_pipeline_sync(
        pdf_path=pdf_path,
        openai_api_key=api_key,
        on_progress=on_progress,
        google_api_key=google_api_key,
    )

    # PaddleOCR LF extraction (module if available, subprocess fallback to Python 3.11)
    lf_data = None
    ocr_indices = sorted({
        p["page"] - 1 for p in result.get("_pages", [])
        if p.get("category") in _OCR_CATEGORIES
    })
    if ocr_indices:
        on_progress("ocr", f"Running LF extraction on {len(ocr_indices)} pages...", 91)
        try:
            lf_data = _run_lf_extraction(pdf_path, ocr_indices)
            if lf_data.get("grand_total_lf"):
                from app.pipeline.aggregate import inject_lf_data
                inject_lf_data(result, lf_data)
                on_progress("ocr", f"LF: {lf_data['grand_total_lf']} ft", 95)
            else:
                on_progress("ocr", "LF extraction returned 0 — skipped", 95)
        except Exception as e:
            on_progress("ocr", f"LF extraction skipped: {e}", 95)
    elapsed = time.time() - t0

    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)

    proj = result.get("project", {})
    print("=" * 60)
    print(f"  Time:      {elapsed/60:.1f} min")
    print(f"  Project:   {proj.get('name', '—')}")
    print(f"  Address:   {proj.get('address', '—')}")
    print(f"  SE:        {proj.get('structural_engineer', '—')}")
    print(f"  Sheets:    {len(proj.get('sheet_list', []))}")
    print(f"  Hardware:  {len(result.get('simpson_hardware', []))} items")
    print(f"  Framing:   {len(result.get('framing_details', []))} connections")
    print(f"  Nailing:   {len(result.get('nailing_schedule', []))} entries")
    print(f"  Lumber:    {len(result.get('lumber_specs', []))} entries")
    print(f"  Concrete:  {len(result.get('concrete_specs', []))} entries")
    foundation = result.get("foundation", {})
    if foundation.get("concrete_cubic_yards"):
        cy = foundation["concrete_cubic_yards"]
        lf = lf_data.get("grand_total_lf", 0) if lf_data else 0
        est = " (est.)" if foundation.get("estimated") else ""
        print(f"  Footing LF:{lf} ft{est}")
        print(f"  Concrete:  {cy} CY{est}")
    print(f"  Output:    {out_file}")


if __name__ == "__main__":
    main()
