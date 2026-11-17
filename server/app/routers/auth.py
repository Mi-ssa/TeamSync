from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.auth import CurrentUser, SessionDep, create_access_token, hash_password, verify_password
from app.models import Usuario
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UsuarioPublic


router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=UsuarioPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: SessionDep) -> Usuario:
    correo = str(payload.correo).strip().lower()
    existing = session.exec(select(Usuario).where(Usuario.correo == correo)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")

    usuario = Usuario(
        nombre=payload.nombre.strip(),
        correo=correo,
        contrasena_hash=hash_password(payload.contrasena),
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    correo = str(payload.correo).strip().lower()
    usuario = session.exec(select(Usuario).where(Usuario.correo == correo)).first()
    if usuario is None or not verify_password(payload.contrasena, usuario.contrasena_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return TokenResponse(access_token=create_access_token(usuario.id))


@router.get("/me", response_model=UsuarioPublic)
def me(usuario: CurrentUser) -> Usuario:
    return usuario
