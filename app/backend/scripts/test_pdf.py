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
import sys
import time
from pathlib import Path

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

    # PaddleOCR passes — shared with the web app (single source of truth, no scope drift)
    from app.pipeline.runner import run_ocr_passes
    run_ocr_passes(pdf_path, result, on_progress)
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
    if foundation.get("total_lf") or foundation.get("concrete_cubic_yards"):
        est = " (est.)" if foundation.get("estimated") else ""
        print(f"  Footing LF:{foundation.get('total_lf', 0)} ft{est}")
        print(f"  Concrete:  {foundation.get('concrete_cubic_yards', 0)} CY{est}")
    print(f"  Output:    {out_file}")


if __name__ == "__main__":
    main()
