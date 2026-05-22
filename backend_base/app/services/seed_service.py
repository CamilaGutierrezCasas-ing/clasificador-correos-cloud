from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.auth_service import create_user, get_role_by_name, get_user_by_email
from app.models.role import Role

settings = get_settings()
DEFAULT_ROLES = ["admin", "secretaria", "usuario"]


def seed_roles(db: Session) -> None:
    for role_name in DEFAULT_ROLES:
        if not get_role_by_name(db, role_name):
            db.add(Role(name=role_name))
    db.commit()


def seed_default_admin(db: Session) -> None:
    if not get_user_by_email(db, settings.default_admin_email):
        create_user(
            db,
            name=settings.default_admin_name,
            email=settings.default_admin_email,
            password=settings.default_admin_password,
            role_name="admin",
        )
