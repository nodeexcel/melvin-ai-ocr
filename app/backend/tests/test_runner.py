from unittest.mock import MagicMock, patch

from app.pipeline.runner import run_pipeline_sync


def test_run_pipeline_sync_calls_progress(tmp_path):
    """Verify that run_pipeline_sync writes progress events and returns a result dict."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    progress_events = []

    def fake_progress(step, message, pct):
        progress_events.append({"step": step, "message": message, "pct": pct})

    with patch("app.pipeline.runner.OpenAI") as mock_openai, \
         patch("app.pipeline.runner.classify_pages") as mock_classify, \
         patch("app.pipeline.runner.render_vision_pages") as mock_render, \
         patch("app.pipeline.runner.extract_all_pages") as mock_extract, \
         patch("app.pipeline.runner.aggregate_results") as mock_aggregate:

        mock_openai.return_value = MagicMock()
        mock_classify.return_value = []
        mock_render.return_value = {}
        mock_extract.return_value = []
        mock_aggregate.return_value = {"project": {"name": "Test"}}

        result = run_pipeline_sync(
            pdf_path=str(pdf_path),
            openai_api_key="fake-key",
            on_progress=fake_progress,
        )

    assert result["project"] == {"name": "Test"}
    assert "quantities" in result  # run_pipeline_sync adds a preliminary quantities estimate
    steps = [e["step"] for e in progress_events]
    assert "classifying" in steps
    assert "extracting" in steps
    assert "aggregating" in steps
