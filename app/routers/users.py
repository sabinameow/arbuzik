from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..models import User
from ..auth import hash_password, verify_password, create_token
from ..dependencies import get_db
from ..audit import log_action
from ..schemas import RegisterRequest, LoginRequest

router = APIRouter(tags=["auth"])

VALID_ROLES = {"admin", "courier", "customer"}


@router.post("/register", summary="Register a new user")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        if body.role not in VALID_ROLES:
            return {"error": f"Role must be one of: {VALID_ROLES}"}

        if db.query(User).filter(User.username == body.username).first():
            return {"error": "Username already taken"}

        user = User(username=body.username, password=hash_password(body.password), role=body.role)
        db.add(user)
        db.commit()
        db.refresh(user)

        log_action(db, user.id, "user_registered", detail=f"role={body.role}")
        return {"message": "User created", "id": user.id, "role": body.role}

    except Exception as e:
        return {"error": str(e)}

@router.post("/login", summary="Login and receive JWT token")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == body.username).first()
        if not user or not verify_password(body.password, user.password):
            return {"error": "Invalid credentials"}

        token = create_token({"id": user.id})
        log_action(db, user.id, "user_login", detail=f"username={body.username}")
        return {"access_token": token, "role": user.role}

    except Exception as e:
        return {"error": str(e)}