from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.role import Role
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_role_by_name(db: Session, role_name: str) -> Role | None:
    return db.query(Role).filter(Role.name == role_name).first()


def create_user(db: Session, *, name: str, email: str, password: str, role_name: str = "usuario") -> User:
    role = get_role_by_name(db, role_name)
    if not role:
        raise ValueError(f"El rol '{role_name}' no existe")

    user = User(
        name=name.strip(),
        email=email.lower().strip(),
        password_hash=get_password_hash(password),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
