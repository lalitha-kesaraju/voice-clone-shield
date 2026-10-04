"""Voiceprint enrollment: upload clean vocals -> ECAPA embedding -> pgvector."""
import os
import time
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import audio, models, schemas
from ..config import settings
from ..database import get_db
from .auth import get_current_user

router = APIRouter(prefix="/api/voiceprints", tags=["voiceprints"])

ALLOWED_EXTS = {".wav", ".flac", ".ogg", ".oga", ".aiff", ".aif", ".mp3", ".m4a"}


def _save_upload(user_id: int, kind: str, upload: UploadFile) -> str:
    ext = os.path.splitext(upload.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type '{ext}'. Use: {', '.join(sorted(ALLOWED_EXTS))}",
        )
    dest_dir = os.path.join(settings.STORAGE_DIR, kind, str(user_id))
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}")
    size = 0
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    with open(dest, "wb") as fh:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                fh.close()
                os.remove(dest)
                raise HTTPException(status_code=413, detail="File exceeds the size limit")
            fh.write(chunk)
    return dest


@router.post("", response_model=schemas.VoiceprintOut, status_code=201)
def enroll_voiceprint(
    label: str = Form(..., min_length=1, max_length=255),
    file: UploadFile = File(...),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enroll a voiceprint from 2-3 minutes of clean vocal audio."""
    path = _save_upload(user.id, "voiceprints", file)
    try:
        embedding, duration, voiced_ratio = audio.embed_clip(path)
    except RuntimeError as exc:  # missing ML deps -> clean 503, keep the upload
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:  # unusable audio
        os.remove(path)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # unreadable file etc.
        os.remove(path)
        raise HTTPException(status_code=422, detail=f"Could not process audio: {exc}")

    vp = models.Voiceprint(
        user_id=user.id,
        label=label.strip(),
        audio_path=path,
        duration_sec=duration,
        voiced_ratio=voiced_ratio,
        embedding=embedding.tolist(),
    )
    db.add(vp)
    db.commit()
    db.refresh(vp)
    return vp


@router.get("", response_model=list[schemas.VoiceprintOut])
def list_voiceprints(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return (
        db.query(models.Voiceprint)
        .filter(models.Voiceprint.user_id == user.id)
        .order_by(models.Voiceprint.created_at.desc())
        .all()
    )


@router.delete("/{voiceprint_id}", status_code=204)
def delete_voiceprint(
    voiceprint_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vp = (
        db.query(models.Voiceprint)
        .filter(models.Voiceprint.id == voiceprint_id, models.Voiceprint.user_id == user.id)
        .first()
    )
    if vp is None:
        raise HTTPException(status_code=404, detail="Voiceprint not found")
    db.delete(vp)
    db.commit()
    try:
        os.remove(vp.audio_path)
    except OSError:
        pass
    return None
