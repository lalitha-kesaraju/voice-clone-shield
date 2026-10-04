"""Database models."""
import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

from .config import settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    artist_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    voiceprints = relationship("Voiceprint", back_populates="user", cascade="all, delete-orphan")
    checks = relationship("MatchCheck", back_populates="user", cascade="all, delete-orphan")


class Voiceprint(Base):
    """An enrolled speaker identity: 192-dim ECAPA-TDNN embedding in pgvector."""

    __tablename__ = "voiceprints"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    audio_path = Column(String(1024), nullable=False)
    duration_sec = Column(Float, nullable=False)
    voiced_ratio = Column(Float, nullable=False, default=0.0)
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="voiceprints")


class MatchCheck(Base):
    """One suspect-clip check: ranked voiceprint matches + artist feedback."""

    __tablename__ = "checks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(1024), nullable=False)
    audio_path = Column(String(1024), nullable=False)
    duration_sec = Column(Float, nullable=False)
    voiced_ratio = Column(Float, nullable=False, default=0.0)
    # [{"voiceprint_id": int, "label": str, "score": float, "band": str}]
    results = Column(JSON, nullable=False, default=list)
    top_score = Column(Float, nullable=False, default=0.0)
    # likely_match | review | no_match
    verdict = Column(String(32), nullable=False, default="no_match")
    # confirmed | rejected | None  (artist feedback loop)
    feedback = Column(String(16), nullable=True)
    feedback_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="checks")
