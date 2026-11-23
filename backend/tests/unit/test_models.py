from app.db.models import Base


def test_models_metadata():
    table_names = Base.metadata.tables.keys()
    expected_tables = [
        "users",
        "departments",
        "memberships",
        "refresh_tokens",
        "documents",
        "chunks",
        "ingestion_jobs",
        "ingestion_job_items",
        "conversations",
        "messages",
        "feedback",
        "audit_log",
    ]
    for tbl in expected_tables:
        assert tbl in table_names, f"Table {tbl} should be defined in Base.metadata"
