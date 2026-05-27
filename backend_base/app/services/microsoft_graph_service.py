from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, quote
import secrets
import html
import re

import httpx
from jose import jwt
from sqlalchemy.orm import Session
import httpx
from typing import Any


from app.core.config import get_settings
from app.core.security import decode_token
from app.models.linked_account import LinkedAccount
from app.models.user import User

settings = get_settings()


def create_microsoft_state(*, user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {
        "sub": f"ms-connect:{user.email}",
        "uid": user.id,
        "typ": "ms_state",
        "nonce": secrets.token_urlsafe(16),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def validate_microsoft_state(state: str) -> int:
    payload = decode_token(state)
    if payload.get("typ") != "ms_state":
        raise ValueError("State inválido")

    user_id = payload.get("uid")
    if not user_id:
        raise ValueError("State sin usuario")

    return int(user_id)


def build_microsoft_authorization_url(*, state: str) -> str:
    base_url = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/authorize"
    query = urlencode(
        {
            "client_id": settings.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": settings.microsoft_redirect_uri,
            "response_mode": "query",
            "scope": settings.microsoft_scopes,
            "state": state,
        }
    )
    return f"{base_url}?{query}"


def exchange_code_for_tokens(*, code: str) -> dict[str, Any]:
    token_url = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.microsoft_redirect_uri,
        "scope": settings.microsoft_scopes,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


def get_microsoft_profile(*, access_token: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://graph.microsoft.com/v1.0/me?$select=id,displayName,mail,userPrincipalName",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def upsert_linked_account(
    db: Session,
    *,
    user_id: int,
    tenant_id: str,
    token_payload: dict[str, Any],
    profile: dict[str, Any],
) -> LinkedAccount:
    account_email = profile.get("mail") or profile.get("userPrincipalName") or "sin-correo@microsoft.local"
    microsoft_user_id = profile["id"]
    display_name = profile.get("displayName") or account_email
    expires_in = int(token_payload.get("expires_in", 3600))
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    account = (
        db.query(LinkedAccount)
        .filter(
            LinkedAccount.user_id == user_id,
            LinkedAccount.provider == "microsoft",
            LinkedAccount.microsoft_user_id == microsoft_user_id,
        )
        .first()
    )

    if account is None:
        account = LinkedAccount(
            user_id=user_id,
            provider="microsoft",
            account_email=account_email,
            display_name=display_name,
            microsoft_user_id=microsoft_user_id,
            tenant_id=tenant_id,
            access_token=token_payload["access_token"],
            refresh_token=token_payload.get("refresh_token") or "",
            token_expires_at=token_expires_at,
            is_active=True,
        )
        db.add(account)
    else:
        account.account_email = account_email
        account.display_name = display_name
        account.tenant_id = tenant_id
        account.access_token = token_payload["access_token"]
        account.refresh_token = token_payload.get("refresh_token") or account.refresh_token
        account.token_expires_at = token_expires_at
        account.is_active = True

    db.commit()
    db.refresh(account)
    return account




def refresh_microsoft_access_token(*, refresh_token: str) -> dict[str, Any]:
    """
    Renueva el access_token usando el refresh_token.
    Esto permite consultar correos en vivo aunque el token inicial ya haya expirado.
    """
    token_url = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token"

    payload = {
        "client_id": settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": settings.microsoft_redirect_uri,
        "scope": settings.microsoft_scopes,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


def get_valid_microsoft_access_token(db: Session, *, account: LinkedAccount) -> str:
    """
    Devuelve un access_token válido.
    Si está próximo a vencer, lo renueva con refresh_token y actualiza SOLO los tokens,
    no el contenido de correos.
    """
    now = datetime.now(timezone.utc)
    expires_at = account.token_expires_at

    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # Si el token todavía sirve por más de 5 minutos, úsalo.
    if account.access_token and expires_at and expires_at > now + timedelta(minutes=5):
        return account.access_token

    if not account.refresh_token:
        return account.access_token

    token_payload = refresh_microsoft_access_token(refresh_token=account.refresh_token)

    expires_in = int(token_payload.get("expires_in", 3600))
    account.access_token = token_payload["access_token"]
    account.refresh_token = token_payload.get("refresh_token") or account.refresh_token
    account.token_expires_at = now + timedelta(seconds=expires_in)
    account.is_active = True

    db.commit()
    db.refresh(account)

    return account.access_token


def list_user_linked_accounts(db: Session, *, user_id: int) -> list[LinkedAccount]:
    return (
        db.query(LinkedAccount)
        .filter(LinkedAccount.user_id == user_id)
        .order_by(LinkedAccount.created_at.desc())
        .all()
    )
def get_account_messages(*, access_token: str, top: int = 1000) -> list[dict[str, Any]]:
    """
    Obtiene correos desde Microsoft Graph usando paginación.
    Trae hasta 'top' correos en total.
    """

    messages: list[dict[str, Any]] = []

    url = (
        "https://graph.microsoft.com/v1.0/me/messages"
        "?$select=id,subject,bodyPreview,receivedDateTime,from"
        "&$top=500"
        "&$orderby=receivedDateTime desc"
    )

    with httpx.Client(timeout=60.0) as client:
        while url and len(messages) < top:
            response = client.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            response.raise_for_status()

            data = response.json()
            batch = data.get("value", [])

            remaining = top - len(messages)
            messages.extend(batch[:remaining])

            url = data.get("@odata.nextLink")

    return messages

def html_to_plain_text(value: str) -> str:
    """Convierte HTML simple de Microsoft Graph a texto legible para mostrarlo sin guardarlo."""
    value = value or ""
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?i)</p>", "\n", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    lines = [line.strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def get_account_message_detail(*, access_token: str, message_id: str) -> dict[str, Any]:
    """
    Obtiene el detalle de un correo directamente desde Microsoft Graph.
    Importante: esta función solo devuelve el contenido para mostrarlo; no lo guarda en BD.
    """
    safe_message_id = quote(message_id, safe="")
    url = (
        f"https://graph.microsoft.com/v1.0/me/messages/{safe_message_id}"
        "?$select=id,subject,bodyPreview,body,receivedDateTime,from"
    )

    with httpx.Client(timeout=60.0) as client:
        response = client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()

    body_data = data.get("body") or {}
    raw_body = body_data.get("content") or data.get("bodyPreview") or ""
    content_type = (body_data.get("contentType") or "").lower()

    if content_type == "html":
        body_text = html_to_plain_text(raw_body)
    else:
        body_text = raw_body

    from_data = data.get("from") or {}
    email_address = from_data.get("emailAddress") or {}

    return {
        "subject": data.get("subject") or "Sin asunto",
        "body": body_text or data.get("bodyPreview") or "Sin contenido disponible",
        "sender": email_address.get("address") or "desconocido",
        "received_at": data.get("receivedDateTime"),
    }
