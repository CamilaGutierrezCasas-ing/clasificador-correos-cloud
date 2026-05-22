from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.user import MessageResponse, TokenResponse, UserLogin, UserOut, UserRegister
from app.services.auth_service import authenticate_user, create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(status_code=401, detail="Ya existe un usuario con ese correo")

    user = create_user(db, name=payload.name, email=payload.email, password=payload.password, role_name="usuario")
    token = create_access_token(subject=user.email, extra_claims={"role": user.role.name})
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_access_token(subject=user.email, extra_claims={"role": user.role.name})
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserOut)
def read_me(current_user=Depends(get_current_user)) -> UserOut:
    return current_user


@router.get("/secretaria-demo", response_model=MessageResponse)
def secretaria_demo(current_user=Depends(require_roles("secretaria", "admin"))) -> MessageResponse:
    return MessageResponse(message=f"Hola {current_user.name}, tienes acceso de secretaria/admin")


@router.get("/admin-demo", response_model=MessageResponse)
def admin_demo(current_user=Depends(require_roles("admin"))) -> MessageResponse:
    return MessageResponse(message=f"Hola {current_user.name}, tienes acceso de administrador")
