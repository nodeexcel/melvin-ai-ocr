def test_models_importable():
    from app.models import AnalysisResult, JobEvent, Project, User
    assert User.__tablename__ == "users"
    assert Project.__tablename__ == "projects"
    assert JobEvent.__tablename__ == "job_events"
    assert AnalysisResult.__tablename__ == "analysis_results"
