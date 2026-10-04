"""Suspect-clip checks: embed -> cosine similarity vs enrolled voiceprints.

v1 is manual-upload only. Automated scanning of YouTube/Instagram/Reels is
explicitly out of scope for v1 (see README: stubbed for v2).
"""
import io

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import audio, evidence, models, schemas
from ..config import settings
from ..database import get_db
from .auth import get_current_user
from .voiceprints import _save_upload

router = APIRouter(prefix="/api/checks", tags=["checks"])


def _rank_against(embedding: np.ndarray, voiceprints: list[models.Voiceprint]):
    ranked = []
    for vp in voiceprints:
        score = audio.cosine_similarity(embedding, np.asarray(vp.embedding, dtype=np.float32))
        ranked.append(
            {
                "voiceprint_id": vp.id,
                "label": vp.label,
                "score": round(score, 4),
                "band": audio.band_for(score),
            }
        )
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked


@router.post("", response_model=schemas.CheckOut, status_code=201)
def run_check(
    file: UploadFile = File(...),
    voiceprint_id: int | None = Form(default=None),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a suspect clip and compare it against enrolled voiceprints."""
    q = db.query(models.Voiceprint).filter(models.Voiceprint.user_id == user.id)
    if voiceprint_id is not None:
        q = q.filter(models.Voiceprint.id == voiceprint_id)
    voiceprints = q.all()
    if not voiceprints:
        raise HTTPException(
            status_code=400,
            detail="No enrolled voiceprints to compare against. Enroll your voice first.",
        )

    path = _save_upload(user.id, "checks", file)
    try:
        embedding, duration, voiced_ratio = audio.embed_clip(path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process audio: {exc}")

    results = _rank_against(embedding, voiceprints)
    top_score = results[0]["score"] if results else 0.0
    verdict = results[0]["band"] if results else "no_match"

    check = models.MatchCheck(
        user_id=user.id,
        filename=file.filename or "upload",
        audio_path=path,
        duration_sec=duration,
        voiced_ratio=voiced_ratio,
        results=results,
        top_score=top_score,
        verdict=verdict,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


@router.get("", response_model=list[schemas.CheckOut])
def list_checks(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return (
        db.query(models.MatchCheck)
        .filter(models.MatchCheck.user_id == user.id)
        .order_by(models.MatchCheck.created_at.desc())
        .all()
    )


@router.get("/{check_id}", response_model=schemas.CheckOut)
def get_check(
    check_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check = _owned_check(check_id, user, db)
    return check


@router.post("/{check_id}/feedback", response_model=schemas.CheckOut)
def submit_feedback(
    check_id: int,
    payload: schemas.FeedbackIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm/reject feedback loop: teaches per-artist thresholds over time (v2)."""
    check = _owned_check(check_id, user, db)
    check.feedback = payload.verdict
    check.feedback_note = payload.note
    db.commit()
    db.refresh(check)
    return check


@router.get("/{check_id}/evidence")
def download_evidence(
    check_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evidence-pack PDF for takedown filing."""
    check = _owned_check(check_id, user, db)
    pdf_bytes = evidence.build_evidence_pdf(
        check, user, settings.MATCH_THRESHOLD, settings.REVIEW_THRESHOLD
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="voice-clone-shield-evidence-{check.id:06d}.pdf"'},
    )


def _owned_check(check_id: int, user: models.User, db: Session) -> models.MatchCheck:
    check = (
        db.query(models.MatchCheck)
        .filter(models.MatchCheck.id == check_id, models.MatchCheck.user_id == user.id)
        .first()
    )
    if check is None:
        raise HTTPException(status_code=404, detail="Check not found")
    return check
