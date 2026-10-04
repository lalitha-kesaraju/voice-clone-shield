"""Central configuration. All secrets come from environment variables only."""
import os

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://shield:shield@localhost:5432/shield",
    )
    # Empty means "not configured" — main.py refuses to boot without it.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "1440"))
    STORAGE_DIR: str = os.path.abspath(
        os.getenv("STORAGE_DIR", os.path.join(_BASE_DIR, "storage"))
    )
    MATCH_THRESHOLD: float = float(os.getenv("MATCH_THRESHOLD", "0.70"))
    REVIEW_THRESHOLD: float = float(os.getenv("REVIEW_THRESHOLD", "0.55"))
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "50"))

    # Audio pipeline constants
    TARGET_SR: int = 16000
    EMBEDDING_DIM: int = 192  # speechbrain/spkrec-ecapa-voxceleb
    MIN_VOICED_RATIO: float = 0.10
    MIN_VOICED_SECONDS: float = 10.0
    CHUNK_SECONDS: int = 30  # long clips are embedded per-chunk and averaged


settings = Settings()
