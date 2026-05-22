import httpx
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.linked_account import LinkedAccount
from app.models.user import User
from app.schemas.microsoft import (
    MicrosoftAccountOut,
    MicrosoftConnectResponse,
)
from app.core.config import get_settings
from app.services.microsoft_graph_service import (
    build_microsoft_authorization_url,
    create_microsoft_state,
    exchange_code_for_tokens,
    get_microsoft_profile,
    list_user_linked_accounts,
    upsert_linked_account,
    validate_microsoft_state,
)

router = APIRouter(prefix="/microsoft", tags=["Microsoft"])


def _frontend_callback_url() -> str:
    return get_settings().frontend_callback_url



@router.get("/connect", response_model=MicrosoftConnectResponse)
def connect_microsoft(
    current_user: User = Depends(get_current_user),
) -> MicrosoftConnectResponse:
    from app.core.config import get_settings

    settings = get_settings()
    state = create_microsoft_state(user=current_user)
    authorization_url = build_microsoft_authorization_url(state=state)

    return MicrosoftConnectResponse(
        authorization_url=authorization_url,
        state=state,
        redirect_uri=settings.microsoft_redirect_uri,
        scopes=settings.microsoft_scope_list,
    )


@router.get("/callback")
def microsoft_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        params = urlencode(
            {
                "status": "error",
                "message": f"Microsoft devolvió error: {error}",
            }
        )
        return RedirectResponse(
            url=f"{_frontend_callback_url()}?{params}",
            status_code=status.HTTP_302_FOUND,
        )

    if not code or not state:
        params = urlencode(
            {
                "status": "error",
                "message": "Falta code o state en el callback",
            }
        )
        return RedirectResponse(
            url=f"{_frontend_callback_url()}?{params}",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        user_id = validate_microsoft_state(state)
    except ValueError as exc:
        params = urlencode(
            {
                "status": "error",
                "message": str(exc),
            }
        )
        return RedirectResponse(
            url=f"{_frontend_callback_url()}?{params}",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        token_payload = exchange_code_for_tokens(code=code)
        profile = get_microsoft_profile(access_token=token_payload["access_token"])

        tenant_id = (
            token_payload.get("id_token_claims", {}).get("tid")
            or token_payload.get("tid")
            or "common"
        )

        account = upsert_linked_account(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            token_payload=token_payload,
            profile=profile,
        )

    except httpx.HTTPStatusError as exc:
        params = urlencode(
            {
                "status": "error",
                "message": f"Error HTTP con Microsoft: {exc.response.text}",
            }
        )
        return RedirectResponse(
            url=f"{_frontend_callback_url()}?{params}",
            status_code=status.HTTP_302_FOUND,
        )

    except Exception as exc:
        params = urlencode(
            {
                "status": "error",
                "message": f"No se pudo vincular la cuenta Microsoft: {exc}",
            }
        )
        return RedirectResponse(
            url=f"{_frontend_callback_url()}?{params}",
            status_code=status.HTTP_302_FOUND,
        )

    params = urlencode(
        {
            "status": "success",
            "message": "Cuenta Microsoft vinculada correctamente",
            "account_email": account.account_email,
        }
    )

    return RedirectResponse(
        url=f"{_frontend_callback_url()}?{params}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/accounts", response_model=list[MicrosoftAccountOut])
def read_my_microsoft_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MicrosoftAccountOut]:
    return list_user_linked_accounts(db=db, user_id=current_user.id)


@router.post("/accounts/{account_id}/disconnect")
def disconnect_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = (
        db.query(LinkedAccount)
        .filter(
            LinkedAccount.id == account_id,
            LinkedAccount.user_id == current_user.id,
        )
        .first()
    )

    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    account.is_active = False

    db.commit()
    db.refresh(account)

    return {"message": "Cuenta Microsoft desconectada correctamente"}