from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.services.email_service import reclassify_all_emails


from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.ml.classifier import MODEL_VERSION, classify_email
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
)
from app.services.email_service import (
    chatbot_email_query,
    create_classified_email,
    get_global_advanced_statistics,
    get_user_email_by_id,
    list_user_emails,
    list_user_emails_by_account,
    list_user_emails_by_category,
    sync_emails_from_microsoft_account,
    update_email_category,
)

router = APIRouter(prefix="/emails", tags=["Emails"])

CONFIDENCE_THRESHOLD = 0.30


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
    return list_user_emails_by_category(
        db,
        owner=current_user,
        category=category,
    )


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
    result = chatbot_email_query(
        db,
        owner=current_user,
        user_query=payload.query,
    )
    return EmailChatbotResponse(**result)


@router.get("/mine/account/{account_id}", response_model=list[EmailOut])
def read_my_emails_by_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailOut]:
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

    return list_user_emails_by_account(
        db,
        owner=current_user,
        linked_account_id=account_id,
    )


@router.post("/sync/{account_id}")
def sync_my_microsoft_emails(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
        raise HTTPException(
            status_code=404,
            detail="Cuenta Microsoft no encontrada o inactiva",
        )

    saved = sync_emails_from_microsoft_account(
        db,
        owner=current_user,
        account=account,
        top=200,
    )

    return {
        "message": "Sincronización completada",
        "account_id": account.id,
        "account_email": account.account_email,
        "synced_count": len(saved),
    }




def _extract_sender_from_graph(message: dict) -> str:
    from_data = message.get("from") or {}
    email_address = from_data.get("emailAddress") or {}
    return email_address.get("address") or "desconocido"


@router.get("/live/account/{account_id}")
def read_live_microsoft_emails(
    account_id: int,
    top: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Consulta correos en vivo desde Microsoft Graph.
    No guarda subject, body ni sender en la tabla emails.
    Solo devuelve la información en la respuesta HTTP para mostrarla en pantalla.
    """
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
        raise HTTPException(
            status_code=404,
            detail="Cuenta Microsoft no encontrada o inactiva",
        )

    try:
        access_token = get_valid_microsoft_access_token(db, account=account)
        messages = get_account_messages(access_token=access_token, top=top)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudieron consultar los correos en vivo desde Microsoft Graph: {str(exc)}",
        )

    result = []

    for message in messages:
        subject = message.get("subject") or "Sin asunto"
        body_preview = message.get("bodyPreview") or ""
        sender = _extract_sender_from_graph(message)

        category, confidence = classify_email(subject, body_preview)

        if confidence < CONFIDENCE_THRESHOLD:
            category = "otros"

        graph_message_id = message.get("id")

        result.append(
            {
                "id": f"live-{graph_message_id}",
                "linked_account_id": account.id,
                "graph_message_id": graph_message_id,
                "subject": subject,
                "body": body_preview,
                "sender": sender,
                "source_account": account.account_email,
                "predicted_category": category,
                "confidence": round(float(confidence), 4),
                "is_synced_from_microsoft": True,
                "is_live": True,
                "received_at": message.get("receivedDateTime"),
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
    """
    Consulta el detalle completo de un correo en vivo desde Microsoft Graph.
    No lo guarda en base de datos.
    """
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
        raise HTTPException(
            status_code=404,
            detail="Cuenta Microsoft no encontrada o inactiva",
        )

    try:
        access_token = get_valid_microsoft_access_token(db, account=account)
        live_detail = get_account_message_detail(
            access_token=access_token,
            message_id=message_id,
        )
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

    return {
        "id": f"live-{message_id}",
        "linked_account_id": account.id,
        "graph_message_id": message_id,
        "subject": subject,
        "body": body,
        "sender": sender,
        "source_account": account.account_email,
        "predicted_category": category,
        "confidence": round(float(confidence), 4),
        "is_synced_from_microsoft": True,
        "is_live": True,
        "received_at": live_detail.get("received_at"),
    }


@router.get("/{email_id}", response_model=EmailOut)
def read_my_email_detail(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailOut:
    email = get_user_email_by_id(db, owner=current_user, email_id=email_id)

    if not email:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    # Privacidad por diseño:
    # En la base de datos NO se guarda el contenido real del correo.
    # Si el correo viene de Microsoft, al abrir el detalle se consulta en vivo a Microsoft Graph
    # y se devuelve solo en la respuesta HTTP, sin hacer db.commit().
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
                live_detail = get_account_message_detail(
                    access_token=account.access_token,
                    message_id=email.graph_message_id,
                )

                return {
                    "id": email.id,
                    "linked_account_id": email.linked_account_id,
                    "graph_message_id": email.graph_message_id,
                    "subject": live_detail.get("subject") or email.subject,
                    "body": live_detail.get("body") or email.body,
                    "sender": live_detail.get("sender") or email.sender,
                    "source_account": email.source_account,
                    "predicted_category": email.predicted_category,
                    "confidence": email.confidence,
                    "is_synced_from_microsoft": email.is_synced_from_microsoft,
                    "received_at": email.received_at,
                }
            except Exception:
                # Si Microsoft Graph falla o el token expiró, devolvemos lo almacenado sin romper la vista.
                return email

    return email



@router.put("/{email_id}/category", response_model=EmailOut)
def update_email_category_endpoint(
    email_id: int,
    payload: EmailCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailOut:
    email = update_email_category(
        db,
        owner=current_user,
        email_id=email_id,
        new_category=payload.category,
    )

    if not email:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    return email


@router.post("/reclassify-all")
def reclassify_all(
    db: Session = Depends(get_db),
):
    return reclassify_all_emails(db)
