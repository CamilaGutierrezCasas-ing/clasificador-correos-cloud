from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.ml.classifier import MODEL_VERSION, classify_email
from app.models.email import Email
from app.models.linked_account import LinkedAccount
from app.models.user import User
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
    reclassify_all_emails,
    sync_emails_from_microsoft_account,
    update_email_category,
)
from app.services.microsoft_graph_service import (
    get_account_message_detail,
    get_account_messages,
    get_valid_microsoft_access_token,
)

try:
    # Si existe en tu proyecto, mejora mucho la velocidad al clasificar varios correos.
    from app.ml.classifier import classify_emails_batch
except ImportError:  # pragma: no cover
    classify_emails_batch = None


router = APIRouter(prefix="/emails", tags=["Emails"])

CONFIDENCE_THRESHOLD = 0.30


class LiveEmailCategoryUpdate(BaseModel):
    """
    Payload para corregir la categoría de un correo consultado en vivo desde Microsoft Graph.

    Privacidad:
    - Se guarda el asunto para reentrenamiento.
    - NO se guarda el body/contenido completo del correo.
    """

    account_id: int
    message_id: str
    category: str
    subject: str | None = None
    sender: str | None = None


def _extract_sender_from_graph(message: dict) -> str:
    from_data = message.get("from") or {}
    email_address = from_data.get("emailAddress") or {}
    return email_address.get("address") or "desconocido"


def _get_active_linked_account(
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
            LinkedAccount.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Cuenta Microsoft no encontrada o inactiva",
        )

    return account


def _find_saved_live_email(
    db: Session,
    *,
    current_user: User,
    account_id: int,
    graph_message_id: str,
) -> Email | None:
    return (
        db.query(Email)
        .filter(
            Email.user_id == current_user.id,
            Email.linked_account_id == account_id,
            Email.graph_message_id == graph_message_id,
        )
        .first()
    )


def _mark_as_manual_correction(email: Email, category: str) -> None:
    """
    Marca campos de corrección si existen en el modelo.
    Esto hace el archivo más tolerante a pequeñas diferencias entre versiones del modelo.
    """
    # Campo principal usado por el sistema.
    email.predicted_category = category
    email.confidence = 1.0

    # Posibles campos usados por estadísticas/reentrenamiento en distintas versiones.
    optional_values = {
        "is_corrected": True,
        "is_manual_correction": True,
        "is_manually_corrected": True,
        "corrected_category": category,
        "manual_category": category,
        "user_category": category,
    }

    for attr, value in optional_values.items():
        if hasattr(email, attr):
            setattr(email, attr, value)


def _live_email_response(
    *,
    email_id: str | int,
    account: LinkedAccount,
    graph_message_id: str,
    subject: str,
    body: str,
    sender: str,
    category: str,
    confidence: float,
    is_live: bool,
    received_at=None,
):
    return {
        "id": email_id,
        "linked_account_id": account.id,
        "graph_message_id": graph_message_id,
        "subject": subject,
        "body": body,
        "sender": sender,
        "source_account": account.account_email,
        "predicted_category": category,
        "confidence": round(float(confidence), 4),
        "is_synced_from_microsoft": True,
        "is_live": is_live,
        "received_at": received_at,
    }


@router.post(
    "/classify",
    response_model=EmailClassifyResponse,
    status_code=status.HTTP_201_CREATED,
)
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
    account = _get_active_linked_account(
        db,
        account_id=account_id,
        current_user=current_user,
    )

    saved = sync_emails_from_microsoft_account(
        db,
        owner=current_user,
        account=account,
        top=1000,
    )

    return {
        "message": "Sincronización completada",
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
    Consulta correos en vivo desde Microsoft Graph.

    Privacidad:
    - Esta consulta NO guarda automáticamente los correos.
    - Solo se guardan correcciones manuales cuando el usuario cambia la categoría.
    - Si un correo ya fue corregido y guardado, se muestra la categoría corregida.
    """
    account = _get_active_linked_account(
        db,
        account_id=account_id,
        current_user=current_user,
    )

    try:
        access_token = get_valid_microsoft_access_token(db, account=account)
        messages = get_account_messages(access_token=access_token, top=top)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudieron consultar los correos en vivo desde "
                f"Microsoft Graph: {str(exc)}"
            ),
        )

    if not messages:
        return []

    # Clasificación en lote si está disponible. Si no, usa clasificación individual.
    if classify_emails_batch is not None:
        items_to_classify = [
            (
                message.get("subject") or "Sin asunto",
                message.get("bodyPreview") or "",
            )
            for message in messages
        ]

        try:
            classifications = classify_emails_batch(items_to_classify)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudieron clasificar los correos en lote: {str(exc)}",
            )
    else:
        classifications = [
            classify_email(
                message.get("subject") or "Sin asunto",
                message.get("bodyPreview") or "",
            )
            for message in messages
        ]

    graph_ids = [message.get("id") for message in messages if message.get("id")]

    saved_by_graph_id: dict[str, Email] = {}

    if graph_ids:
        saved_emails = (
            db.query(Email)
            .filter(
                Email.user_id == current_user.id,
                Email.linked_account_id == account.id,
                Email.graph_message_id.in_(graph_ids),
            )
            .all()
        )
        saved_by_graph_id = {
            saved_email.graph_message_id: saved_email
            for saved_email in saved_emails
            if saved_email.graph_message_id
        }

    result = []

    for message, (category, confidence) in zip(messages, classifications):
        subject = message.get("subject") or "Sin asunto"
        body_preview = message.get("bodyPreview") or ""
        sender = _extract_sender_from_graph(message)
        graph_message_id = message.get("id")

        if confidence < CONFIDENCE_THRESHOLD:
            category = "otros"

        saved_email = saved_by_graph_id.get(graph_message_id)

        if saved_email:
            # Si ya fue corregido, mostramos la categoría persistida.
            category = saved_email.predicted_category
            confidence = saved_email.confidence or 1.0

        result.append(
            _live_email_response(
                email_id=f"live-{graph_message_id}",
                account=account,
                graph_message_id=graph_message_id,
                subject=subject,
                body=body_preview,
                sender=sender,
                category=category,
                confidence=confidence,
                is_live=True,
                received_at=message.get("receivedDateTime"),
            )
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
    No guarda el contenido en base de datos.
    """
    account = _get_active_linked_account(
        db,
        account_id=account_id,
        current_user=current_user,
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
            detail=(
                "No se pudo consultar el detalle del correo en vivo desde "
                f"Microsoft Graph: {str(exc)}"
            ),
        )

    subject = live_detail.get("subject") or "Sin asunto"
    body = live_detail.get("body") or ""
    sender = live_detail.get("sender") or "desconocido"

    category, confidence = classify_email(subject, body)

    if confidence < CONFIDENCE_THRESHOLD:
        category = "otros"

    saved_email = _find_saved_live_email(
        db,
        current_user=current_user,
        account_id=account.id,
        graph_message_id=message_id,
    )

    if saved_email:
        category = saved_email.predicted_category
        confidence = saved_email.confidence or 1.0

    return _live_email_response(
        email_id=f"live-{message_id}",
        account=account,
        graph_message_id=message_id,
        subject=subject,
        body=body,
        sender=sender,
        category=category,
        confidence=confidence,
        is_live=True,
        received_at=live_detail.get("received_at"),
    )


@router.put("/live/category", response_model=EmailOut)
def update_live_email_category_endpoint(
    payload: LiveEmailCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailOut:
    """
    Corrige la categoría de un correo en vivo de Microsoft Graph.

    Privacidad:
    - Guarda SOLO el asunto, remitente, cuenta, id de Graph y categoría corregida.
    - NO guarda el body/contenido completo del correo.
    - Esto permite que el panel admin y el reentrenamiento usen correcciones reales.
    """
    category = (payload.category or "").strip()
    message_id = (payload.message_id or "").strip()
    subject = (payload.subject or "Sin asunto").strip() or "Sin asunto"
    sender = (payload.sender or "desconocido").strip() or "desconocido"

    if not category:
        raise HTTPException(
            status_code=400,
            detail="La categoría no puede estar vacía",
        )

    if not message_id:
        raise HTTPException(
            status_code=400,
            detail="El message_id del correo en vivo es obligatorio",
        )

    account = _get_active_linked_account(
        db,
        account_id=payload.account_id,
        current_user=current_user,
    )

    existing_email = _find_saved_live_email(
        db,
        current_user=current_user,
        account_id=account.id,
        graph_message_id=message_id,
    )

    if existing_email:
        # Usa el servicio existente para mantener la misma lógica del proyecto.
        updated_email = update_email_category(
            db,
            owner=current_user,
            email_id=existing_email.id,
            new_category=category,
        )

        if not updated_email:
            raise HTTPException(status_code=404, detail="Correo no encontrado")

        _mark_as_manual_correction(updated_email, category)
        db.commit()
        db.refresh(updated_email)
        return updated_email

    # Se guarda solo lo mínimo para privacidad y reentrenamiento.
    # Body vacío a propósito: NO almacenamos contenido del correo.
    email = create_classified_email(
        db,
        owner=current_user,
        subject=subject,
        body="",
        sender=sender,
        source_account=account.account_email,
        predicted_category=category,
        confidence=1.0,
    )

    email.linked_account_id = account.id
    email.graph_message_id = message_id
    email.is_synced_from_microsoft = True
    _mark_as_manual_correction(email, category)

    db.commit()
    db.refresh(email)

    return email


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
    if (
        email.is_synced_from_microsoft
        and email.linked_account_id
        and email.graph_message_id
    ):
        account = (
            db.query(LinkedAccount)
            .filter(
                LinkedAccount.id == email.linked_account_id,
                LinkedAccount.user_id == current_user.id,
                LinkedAccount.is_active == True,  # noqa: E712
            )
            .first()
        )

        if account:
            try:
                access_token = get_valid_microsoft_access_token(db, account=account)
                live_detail = get_account_message_detail(
                    access_token=access_token,
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

    _mark_as_manual_correction(email, payload.category)
    db.commit()
    db.refresh(email)

    return email


@router.post("/reclassify-all")
def reclassify_all(
    db: Session = Depends(get_db),
):
    return reclassify_all_emails(db)
