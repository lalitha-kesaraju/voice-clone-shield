"""Auth endpoints: signup / login / me. Bearer-JWT, PBKDF2 password hashing."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    try:
        user_id = security.decode_token(creds.credentials, settings.JWT_SECRET)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


def _issue_token(user: models.User) -> schemas.TokenOut:
    token = security.create_token(user.id, settings.JWT_SECRET, settings.ACCESS_TOKEN_MINUTES)
    return schemas.TokenOut(access_token=token)


@router.post("/signup", response_model=schemas.TokenOut, status_code=201)
def signup(payload: schemas.SignupIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    user = models.User(
        email=email,
        artist_name=payload.artist_name.strip(),
        password_hash=security.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _issue_token(user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
