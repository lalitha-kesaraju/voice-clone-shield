"""Pydantic request/response schemas (Pydantic v2)."""
import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Auth ----------

class SignupIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    artist_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    artist_name: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ---------- Voiceprints ----------

class VoiceprintOut(BaseModel):
    id: int
    label: str
    duration_sec: float
    voiced_ratio: float
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ---------- Checks ----------

class MatchResult(BaseModel):
    voiceprint_id: int
    label: str
    score: float
    band: str  # likely_match | review | no_match


class CheckOut(BaseModel):
    id: int
    filename: str
    duration_sec: float
    voiced_ratio: float
    results: List[MatchResult]
    top_score: float
    verdict: str
    feedback: Optional[str] = None
    feedback_note: Optional[str] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class FeedbackIn(BaseModel):
    verdict: str = Field(pattern="^(confirmed|rejected)$")
    note: Optional[str] = Field(default=None, max_length=2000)
