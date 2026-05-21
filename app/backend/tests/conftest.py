import os

# Provide dummy env vars so Settings() can be instantiated during test collection.
# The roundtrip test uses its own in-memory SQLite engine and never touches these values.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
