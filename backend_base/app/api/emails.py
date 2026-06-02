from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.ml.classifier import MODEL_VERSION, classify_email, classify_emails_batch
from app.models.linked_account import LinkedAccount
from app.models.user import User
from app.services.microsoft_graph_service import (
    get_account_message_detail,
    get_account_messages,
    get_valid_microsoft_access_token,
)
from app.schemas.email import (
    EmailCategoryUpdate,
    EmailChatbotQuery,
    EmailChatbotResponse,
    EmailClassifyIn,
    EmailClassifyResponse,
    EmailOut,
    LiveEmailCategoryUpdate,
)
from app.services.email_service import (
    chatbot_email_query,
    create_classified_email,
    get_global_advanced_statistics,
    get_user_email_by_id,
    list_user_emails,
    list_user_emails_by_account,
    list_user_emails_by_category,
    parse_graph_datetime,
    reclassify_all_emails,
    sync_emails_from_microsoft_account,
    update_email_category,
    update_microsoft_email_correction,
    upsert_microsoft_email_metadata,
    upsert_microsoft_email_metadata_bulk,
)

router = APIRouter(prefix="/emails", tags=["Emails"])
CONFIDENCE_THRESHOLD = 0.30


def _get_active_account_for_user(
    db: Session,
    *,
    account_id: int,
    current_user: User,
) -> LinkedAccount:
    account = (
        db.query(LinkedAccount)
        .filter(
            LinkedAccount.id == account_id,
            LinkedAccount.user_id == current_user.id,
            LinkedAccount.is_active == True,
        )
        .first()
    )

    if not account:
        raise HTTPException(status_code=404, detail="Cuenta Microsoft no encontrada o inactiva")

    return account


def _extract_sender_from_graph(message: dict) -> str:
    from_data = message.get("from") or {}
    email_address = from_data.get("emailAddress") or {}
    return email_address.get("address") or "desconocido"


@router.post("/classify", response_model=EmailClassifyResponse, status_code=status.HTTP_201_CREATED)
def classify_and_save_email(
    payload: EmailClassifyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailClassifyResponse:
    category, confidence = classify_email(payload.subject, payload.body)
    if confidence < CONFIDENCE_THRESHOLD:
        category = "otros"

    email = create_classified_email(
        db,
        owner=current_user,
        subject=payload.subject,
        body=payload.body,
        sender=payload.sender,
        source_account=payload.source_account,
        predicted_category=category,
        confidence=confidence,
        store_content=False,
    )
    return EmailClassifyResponse(email=email, model_version=MODEL_VERSION)


@router.get("/mine", response_model=list[EmailOut])
def read_my_emails(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailOut]:
    return list_user_emails(db, owner=current_user)


@router.get("/mine/category/{category}", response_model=list[EmailOut])
def read_my_emails_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailOut]:
    return list_user_emails_by_category(db, owner=current_user, category=category)


@router.get("/stats/advanced")
def get_advanced_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "secretaria")),
):
    return get_global_advanced_statistics(db)


@router.post("/chatbot/query", response_model=EmailChatbotResponse)
def chatbot_query_endpoint(
    payload: EmailChatbotQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailChatbotResponse:
    result = chatbot_email_query(db, owner=current_user, user_query=payload.query)
    return EmailChatbotResponse(**result)


@router.get("/mine/account/{account_id}", response_model=list[EmailOut])
def read_my_emails_by_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailOut]:
    account = (
        db.query(LinkedAccount)
        .filter(LinkedAccount.id == account_id, LinkedAccount.user_id == current_user.id)
        .first()
    )

    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    return list_user_emails_by_account(db, owner=current_user, linked_account_id=account_id)


@router.post("/sync/{account_id}")
def sync_my_microsoft_emails(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = _get_active_account_for_user(db, account_id=account_id, current_user=current_user)
    saved = sync_emails_from_microsoft_account(db, owner=current_user, account=account, top=1000)

    return {
        "message": "Sincronización completada sin almacenar contenido del correo",
        "account_id": account.id,
        "account_email": account.account_email,
        "synced_count": len(saved),
    }


@router.get("/live/account/{account_id}")
def read_live_microsoft_emails(
    account_id: int,
    top: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Consulta correos en vivo y guarda SOLO metadatos mínimos.

    Optimización aplicada:
    - Graph trae páginas grandes.
    - El modelo clasifica en lote.
    - La base de datos guarda/actualiza en lote con un solo commit.
    """
    account = _get_active_account_for_user(db, account_id=account_id, current_user=current_user)

    try:
        access_token = get_valid_microsoft_access_token(db, account=account)
        messages = get_account_messages(access_token=access_token, top=top)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudieron consultar los correos en vivo desde Microsoft Graph: {str(exc)}",
        )

    email_pairs: list[tuple[str, str]] = []
    display_items: list[dict] = []

    for message in messages:
        graph_message_id = message.get("id")
        if not graph_message_id:
            continue

        subject = message.get("subject") or "Sin asunto"
        body_preview = message.get("bodyPreview") or ""
        sender = _extract_sender_from_graph(message)
        received_at = parse_graph_datetime(message.get("receivedDateTime"))

        email_pairs.append((subject, body_preview))
        display_items.append(
            {
                "graph_message_id": graph_message_id,
                "subject": subject,
                "body": body_preview,
                "sender": sender,
                "received_at": received_at,
                "received_at_raw": message.get("receivedDateTime"),
            }
        )

    classifications = classify_emails_batch(email_pairs)

    metadata_items: list[dict] = []
    for item, (category, confidence) in zip(display_items, classifications):
        if confidence < CONFIDENCE_THRESHOLD:
            category = "otros"
        metadata_items.append(
            {
                "graph_message_id": item["graph_message_id"],
                "predicted_category": category,
                "confidence": float(confidence),
                "received_at": item["received_at"],
            }
        )

    stored_by_graph_id = upsert_microsoft_email_metadata_bulk(
        db,
        owner=current_user,
        account=account,
        items=metadata_items,
    )

    result = []
    for item in display_items:
        stored_email = stored_by_graph_id.get(item["graph_message_id"])
        if not stored_email:
            continue

        result.append(
            {
                "id": f"live-{item['graph_message_id']}",
                "linked_account_id": account.id,
                "graph_message_id": item["graph_message_id"],
                "subject": item["subject"],
                "body": item["body"],
                "sender": item["sender"],
                "source_account": account.account_email,
                "predicted_category": stored_email.predicted_category,
                "original_category": stored_email.original_category,
                "was_corrected": stored_email.was_corrected,
                "confidence": round(float(stored_email.confidence or 0.0), 4),
                "is_synced_from_microsoft": True,
                "is_live": True,
                "received_at": item["received_at_raw"],
            }
        )

    return result


@router.get("/live/detail")
def read_live_microsoft_email_detail(
    account_id: int = Query(...),
    message_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = _get_active_account_for_user(db, account_id=account_id, current_user=current_user)

    try:
        access_token = get_valid_microsoft_access_token(db, account=account)
        live_detail = get_account_message_detail(access_token=access_token, message_id=message_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo consultar el detalle del correo en vivo desde Microsoft Graph: {str(exc)}",
        )

    subject = live_detail.get("subject") or "Sin asunto"
    body = live_detail.get("body") or ""
    sender = live_detail.get("sender") or "desconocido"

    category, confidence = classify_email(subject, body)
    if confidence < CONFIDENCE_THRESHOLD:
        category = "otros"

    stored_email = upsert_microsoft_email_metadata(
        db,
        owner=current_user,
        account=account,
        graph_message_id=message_id,
        predicted_category=category,
        confidence=float(confidence),
        received_at=parse_graph_datetime(live_detail.get("received_at")),
    )

    return {
        "id": f"live-{message_id}",
        "linked_account_id": account.id,
        "graph_message_id": message_id,
        "subject": subject,
        "body": body,
        "sender": sender,
        "source_account": account.account_email,
        "predicted_category": stored_email.predicted_category,
        "original_category": stored_email.original_category,
        "was_corrected": stored_email.was_corrected,
        "confidence": round(float(stored_email.confidence or 0.0), 4),
        "is_synced_from_microsoft": True,
        "is_live": True,
        "received_at": live_detail.get("received_at"),
    }


@router.put("/live/category", response_model=EmailOut)
def update_live_email_category_endpoint(
    payload: LiveEmailCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailOut:
    account = _get_active_account_for_user(db, account_id=payload.account_id, current_user=current_user)
    return update_microsoft_email_correction(
        db,
        owner=current_user,
        account=account,
        graph_message_id=payload.message_id,
        corrected_category=payload.category,
    )


@router.get("/{email_id}", response_model=EmailOut)
def read_my_email_detail(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailOut:
    email = get_user_email_by_id(db, owner=current_user, email_id=email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    if email.is_synced_from_microsoft and email.linked_account_id and email.graph_message_id:
        account = (
            db.query(LinkedAccount)
            .filter(
                LinkedAccount.id == email.linked_account_id,
                LinkedAccount.user_id == current_user.id,
                LinkedAccount.is_active == True,
            )
            .first()
        )

        if account:
            try:
                access_token = get_valid_microsoft_access_token(db, account=account)
                live_detail = get_account_message_detail(access_token=access_token, message_id=email.graph_message_id)
                return {
                    "id": email.id,
                    "linked_account_id": email.linked_account_id,
                    "graph_message_id": email.graph_message_id,
                    "subject": live_detail.get("subject") or "Sin asunto",
                    "body": live_detail.get("body") or "",
                    "sender": live_detail.get("sender") or "desconocido",
                    "source_account": email.source_account,
                    "predicted_category": email.predicted_category,
                    "original_category": email.original_category,
                    "was_corrected": email.was_corrected,
                    "confidence": email.confidence,
                    "is_synced_from_microsoft": email.is_synced_from_microsoft,
                    "received_at": email.received_at,
                }
            except Exception:
                return email

    return email


@router.put("/{email_id}/category", response_model=EmailOut)
def update_email_category_endpoint(
    email_id: int,
    payload: EmailCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailOut:
    email = update_email_category(db, owner=current_user, email_id=email_id, new_category=payload.category)
    if not email:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    return email


@router.post("/reclassify-all")
def reclassify_all(db: Session = Depends(get_db)):
    return reclassify_all_emails(db)
