from datetime import datetime
from collections import Counter, defaultdict

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ml.classifier import classify_email
from app.models.email import Email
from app.models.linked_account import LinkedAccount
from app.models.user import User
from app.services.microsoft_graph_service import (
    get_account_message_detail,
    get_account_messages,
    get_valid_microsoft_access_token,
)

CONFIDENCE_THRESHOLD = 0.30
LOW_CONFIDENCE_STATS_THRESHOLD = 0.20

# Privacidad por diseño: estos valores se guardan en BD en lugar del contenido real.
PRIVACY_SUBJECT_PLACEHOLDER = "[Contenido no almacenado por privacidad]"
PRIVACY_BODY_PLACEHOLDER = ""
PRIVACY_SENDER_PLACEHOLDER = "[Remitente no almacenado]"


def mask_email_address(value: str) -> str:
    """
    Evita guardar el correo completo del remitente.
    Conserva solo el dominio para análisis básico, por ejemplo: *@empresa.com.
    """
    value = (value or "").strip()
    if "@" not in value:
        return PRIVACY_SENDER_PLACEHOLDER

    domain = value.split("@", 1)[1].strip()
    if not domain:
        return PRIVACY_SENDER_PLACEHOLDER

    return f"*@{domain}"


def normalize_category(value: str) -> str:
    return (value or "otros").strip().lower()


def parse_graph_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def create_classified_email(
    db: Session,
    *,
    owner: User,
    subject: str,
    body: str,
    sender: str,
    source_account: str,
    predicted_category: str,
    confidence: float,
    linked_account_id: int | None = None,
    graph_message_id: str | None = None,
    is_synced_from_microsoft: bool = False,
    received_at: datetime | None = None,
    store_content: bool = False,
) -> Email:
    """
    Crea un correo clasificado.

    Por defecto NO guarda subject/body/sender reales. Solo guarda placeholders/metadatos.
    """
    original_subject = (subject or "").strip()
    original_body = (body or "").strip()
    original_sender = (sender or "desconocido").strip()

    if store_content:
        stored_subject = original_subject
        stored_body = original_body
        stored_sender = original_sender
    else:
        stored_subject = PRIVACY_SUBJECT_PLACEHOLDER
        stored_body = PRIVACY_BODY_PLACEHOLDER
        stored_sender = mask_email_address(original_sender)

    source_account = (source_account or "local-demo").strip()
    predicted_category = normalize_category(predicted_category)

    email = Email(
        owner_user_id=owner.id,
        linked_account_id=linked_account_id,
        graph_message_id=graph_message_id,
        subject=stored_subject,
        body=stored_body,
        sender=stored_sender,
        source_account=source_account,
        original_category=predicted_category,
        predicted_category=predicted_category,
        confidence=float(confidence or 0.0),
        was_corrected=False,
        is_synced_from_microsoft=is_synced_from_microsoft,
        received_at=received_at or datetime.utcnow(),
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return email


def get_email_by_graph_message_id(
    db: Session,
    *,
    graph_message_id: str,
    owner_user_id: int | None = None,
    linked_account_id: int | None = None,
) -> Email | None:
    query = db.query(Email).filter(Email.graph_message_id == graph_message_id)

    if owner_user_id is not None:
        query = query.filter(Email.owner_user_id == owner_user_id)

    if linked_account_id is not None:
        query = query.filter(Email.linked_account_id == linked_account_id)

    return query.first()


def upsert_microsoft_email_metadata(
    db: Session,
    *,
    owner: User,
    account: LinkedAccount,
    graph_message_id: str,
    predicted_category: str,
    confidence: float,
    received_at: datetime | None = None,
) -> Email:
    """
    Guarda o actualiza SOLO metadatos del correo de Microsoft Graph.

    NO guarda subject.
    NO guarda body.
    NO guarda bodyPreview.
    NO guarda remitente real.

    Si el usuario ya corrigió la categoría, se conserva la categoría corregida.
    """
    predicted_category = normalize_category(predicted_category)

    email = get_email_by_graph_message_id(
        db,
        graph_message_id=graph_message_id,
        owner_user_id=owner.id,
        linked_account_id=account.id,
    )

    if email:
        # Mantener el registro actualizado sin borrar correcciones manuales.
        email.source_account = account.account_email
        email.is_synced_from_microsoft = True
        email.linked_account_id = account.id
        if received_at:
            email.received_at = received_at

        if not email.was_corrected:
            email.original_category = predicted_category
            email.predicted_category = predicted_category
            email.confidence = float(confidence or 0.0)

        # Reforzar privacidad por si algún registro antiguo tenía contenido real.
        email.subject = PRIVACY_SUBJECT_PLACEHOLDER
        email.body = PRIVACY_BODY_PLACEHOLDER
        email.sender = PRIVACY_SENDER_PLACEHOLDER

        db.commit()
        db.refresh(email)
        return email

    email = Email(
        owner_user_id=owner.id,
        linked_account_id=account.id,
        graph_message_id=graph_message_id,
        subject=PRIVACY_SUBJECT_PLACEHOLDER,
        body=PRIVACY_BODY_PLACEHOLDER,
        sender=PRIVACY_SENDER_PLACEHOLDER,
        source_account=account.account_email,
        original_category=predicted_category,
        predicted_category=predicted_category,
        confidence=float(confidence or 0.0),
        was_corrected=False,
        is_synced_from_microsoft=True,
        received_at=received_at or datetime.utcnow(),
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return email


def update_microsoft_email_correction(
    db: Session,
    *,
    owner: User,
    account: LinkedAccount,
    graph_message_id: str,
    corrected_category: str,
) -> Email:
    """
    Guarda la corrección manual sin almacenar contenido real del correo.
    El campo predicted_category queda como la categoría final actual.
    El campo original_category conserva la predicción inicial del modelo.
    """
    corrected_category = normalize_category(corrected_category)

    email = get_email_by_graph_message_id(
        db,
        graph_message_id=graph_message_id,
        owner_user_id=owner.id,
        linked_account_id=account.id,
    )

    if not email:
        email = Email(
            owner_user_id=owner.id,
            linked_account_id=account.id,
            graph_message_id=graph_message_id,
            subject=PRIVACY_SUBJECT_PLACEHOLDER,
            body=PRIVACY_BODY_PLACEHOLDER,
            sender=PRIVACY_SENDER_PLACEHOLDER,
            source_account=account.account_email,
            original_category=None,
            predicted_category=corrected_category,
            confidence=1.0,
            was_corrected=True,
            is_synced_from_microsoft=True,
            received_at=datetime.utcnow(),
        )
        db.add(email)
    else:
        if not email.original_category:
            email.original_category = email.predicted_category
        email.predicted_category = corrected_category
        email.confidence = 1.0
        email.was_corrected = True
        email.source_account = account.account_email
        email.is_synced_from_microsoft = True
        email.subject = PRIVACY_SUBJECT_PLACEHOLDER
        email.body = PRIVACY_BODY_PLACEHOLDER
        email.sender = PRIVACY_SENDER_PLACEHOLDER

    db.commit()
    db.refresh(email)
    return email


def list_user_emails(db: Session, *, owner: User) -> list[Email]:
    return (
        db.query(Email)
        .outerjoin(LinkedAccount, Email.linked_account_id == LinkedAccount.id)
        .filter(
            Email.owner_user_id == owner.id,
            or_(
                Email.linked_account_id == None,
                LinkedAccount.is_active == True,
            ),
        )
        .order_by(Email.received_at.desc())
        .all()
    )


def list_user_emails_by_account(
    db: Session,
    *,
    owner: User,
    linked_account_id: int,
) -> list[Email]:
    return (
        db.query(Email)
        .join(LinkedAccount, Email.linked_account_id == LinkedAccount.id)
        .filter(
            Email.owner_user_id == owner.id,
            Email.linked_account_id == linked_account_id,
            LinkedAccount.is_active == True,
        )
        .order_by(Email.received_at.desc())
        .all()
    )


def list_user_emails_by_category(
    db: Session,
    *,
    owner: User,
    category: str,
) -> list[Email]:
    category = normalize_category(category)

    return (
        db.query(Email)
        .outerjoin(LinkedAccount, Email.linked_account_id == LinkedAccount.id)
        .filter(
            Email.owner_user_id == owner.id,
            Email.predicted_category == category,
            or_(
                Email.linked_account_id == None,
                LinkedAccount.is_active == True,
            ),
        )
        .order_by(Email.received_at.desc())
        .all()
    )


def get_user_email_by_id(db: Session, *, owner: User, email_id: int) -> Email | None:
    return (
        db.query(Email)
        .filter(
            Email.owner_user_id == owner.id,
            Email.id == email_id,
        )
        .first()
    )


def update_email_category(
    db: Session,
    *,
    owner: User,
    email_id: int,
    new_category: str,
) -> Email | None:
    new_category = normalize_category(new_category)

    email = (
        db.query(Email)
        .filter(
            Email.id == email_id,
            Email.owner_user_id == owner.id,
        )
        .first()
    )

    if not email:
        return None

    if not email.original_category:
        email.original_category = email.predicted_category

    if email.predicted_category != new_category:
        email.predicted_category = new_category
        email.confidence = 1.0
        email.was_corrected = True

    # Reforzar privacidad en registros existentes.
    if email.is_synced_from_microsoft:
        email.subject = PRIVACY_SUBJECT_PLACEHOLDER
        email.body = PRIVACY_BODY_PLACEHOLDER
        email.sender = PRIVACY_SENDER_PLACEHOLDER

    db.commit()
    db.refresh(email)
    return email


def sync_emails_from_microsoft_account(
    db: Session,
    *,
    owner: User,
    account: LinkedAccount,
    top: int = 1000,
) -> list[Email]:
    """
    Sincroniza metadatos mínimos de Microsoft Graph.
    No guarda contenido del correo.
    """
    access_token = get_valid_microsoft_access_token(db, account=account)
    messages = get_account_messages(access_token=access_token, top=top)
    saved_emails: list[Email] = []

    for msg in messages:
        graph_message_id = msg.get("id")
        if not graph_message_id:
            continue

        subject = msg.get("subject") or ""
        body_preview = msg.get("bodyPreview") or ""
        received_at = parse_graph_datetime(msg.get("receivedDateTime"))

        category, confidence = classify_email(subject, body_preview)
        if confidence < CONFIDENCE_THRESHOLD:
            category = "otros"

        email = upsert_microsoft_email_metadata(
            db,
            owner=owner,
            account=account,
            graph_message_id=graph_message_id,
            predicted_category=category,
            confidence=float(confidence),
            received_at=received_at,
        )
        saved_emails.append(email)

    return saved_emails


def get_advanced_statistics(db: Session, *, owner: User) -> dict:
    emails = (
        db.query(Email)
        .outerjoin(LinkedAccount, Email.linked_account_id == LinkedAccount.id)
        .filter(
            Email.owner_user_id == owner.id,
            Email.source_account != "local-demo",
            or_(
                Email.linked_account_id == None,
                LinkedAccount.is_active == True,
            ),
        )
        .all()
    )
    return build_statistics_from_emails(emails)


def get_global_advanced_statistics(db: Session) -> dict:
    emails = (
        db.query(Email)
        .outerjoin(LinkedAccount, Email.linked_account_id == LinkedAccount.id)
        .filter(
            Email.source_account != "local-demo",
            or_(
                Email.linked_account_id == None,
                LinkedAccount.is_active == True,
            ),
        )
        .all()
    )
    return build_statistics_from_emails(emails, include_global_breakdowns=True)


def build_statistics_from_emails(emails: list[Email], include_global_breakdowns: bool = False) -> dict:
    total = len(emails)

    empty = {
        "total_emails": 0,
        "by_category": {},
        "average_confidence": 0,
        "low_confidence_count": 0,
        "manual_corrections": 0,
        "confusion_matrix": {},
    }

    if include_global_breakdowns:
        empty.update({"by_account": {}, "by_user": {}})

    if total == 0:
        return empty

    categories = [e.predicted_category for e in emails if e.predicted_category]
    category_counts = Counter(categories)
    avg_conf = sum((e.confidence or 0.0) for e in emails) / total
    low_conf = len([e for e in emails if (e.confidence or 0.0) < LOW_CONFIDENCE_STATS_THRESHOLD])
    corrected = len([e for e in emails if e.was_corrected])

    matrix = defaultdict(lambda: defaultdict(int))
    for e in emails:
        original = (e.original_category or "sin_dato").lower()
        final = (e.predicted_category or "sin_dato").lower()
        matrix[original][final] += 1

    result = {
        "total_emails": total,
        "by_category": dict(category_counts),
        "average_confidence": round(avg_conf, 4),
        "low_confidence_count": low_conf,
        "manual_corrections": corrected,
        "confusion_matrix": {k: dict(v) for k, v in matrix.items()},
    }

    if include_global_breakdowns:
        accounts = [e.source_account for e in emails if e.source_account]
        users = [e.owner_user_id for e in emails if e.owner_user_id is not None]
        result["by_account"] = dict(Counter(accounts))
        result["by_user"] = dict(Counter(users))

    return result


def parse_chatbot_query(query: str) -> tuple[str, dict]:
    text = (query or "").strip().lower()
    filters = {
        "category": None,
        "sender_contains": None,
        "text_contains": None,
    }
    intent = "search"

    categories = ["urgente", "trabajo", "educacion", "spam", "otros", "salud"]
    for category in categories:
        if category in text:
            filters["category"] = category
            break

    common_senders = ["nu", "linkedin", "outlook", "bancolombia", "nequi"]
    for sender in common_senders:
        if sender in text:
            filters["sender_contains"] = sender
            break

    trigger_words = [
        "resume", "resumir", "resumen", "mostrar", "muestrame", "muéstrame",
        "buscar", "busca", "que", "qué", "tengo", "mis", "correos", "de", "del",
    ]
    cleaned_text = text
    for word in trigger_words:
        cleaned_text = cleaned_text.replace(word, " ")
    cleaned_text = " ".join(cleaned_text.split())

    if cleaned_text and not filters["sender_contains"] and not filters["category"]:
        filters["text_contains"] = cleaned_text

    if "resume" in text or "resumen" in text or "resumir" in text:
        intent = "summary"

    return intent, filters


def search_emails_for_chatbot(
    db: Session,
    *,
    owner: User,
    filters: dict,
    limit: int = 10,
) -> list[Email]:
    query = db.query(Email).filter(Email.owner_user_id == owner.id)

    if filters.get("category"):
        query = query.filter(Email.predicted_category == filters["category"])

    # Por privacidad, sender/text search puede no encontrar contenido real porque no se guarda.
    if filters.get("sender_contains"):
        sender_value = f"%{filters['sender_contains']}%"
        query = query.filter(Email.sender.ilike(sender_value))

    if filters.get("text_contains"):
        text_value = f"%{filters['text_contains']}%"
        query = query.filter(or_(Email.subject.ilike(text_value), Email.body.ilike(text_value)))

    return query.order_by(Email.received_at.desc()).limit(limit).all()


def build_chatbot_summary(filters: dict, emails: list[Email]) -> str:
    if not emails:
        return "No encontré correos que coincidan con esa consulta."

    total = len(emails)
    category = filters.get("category")
    sender = filters.get("sender_contains")
    text_contains = filters.get("text_contains")

    parts = [f"Encontré {total} correos"]
    if category:
        parts.append(f"de la categoría '{category}'")
    if sender:
        parts.append(f"del remitente relacionado con '{sender}'")
    if text_contains:
        parts.append(f"relacionados con '{text_contains}'")

    summary = " ".join(parts) + "."
    summary += " Por privacidad, no se almacenan asuntos ni cuerpos completos de correos."
    return summary


def chatbot_email_query(db: Session, *, owner: User, user_query: str) -> dict:
    intent, filters = parse_chatbot_query(user_query)
    emails = search_emails_for_chatbot(db, owner=owner, filters=filters, limit=10)
    summary = build_chatbot_summary(filters, emails)
    return {
        "intent": intent,
        "applied_filters": filters,
        "total_results": len(emails),
        "summary": summary,
        "emails": emails,
    }


def reclassify_all_emails(db: Session):
    """
    Reclasifica correos de Microsoft consultando temporalmente Microsoft Graph.
    No guarda contenido del correo; solo actualiza categoría/confianza.
    """
    emails = (
        db.query(Email)
        .outerjoin(LinkedAccount, Email.linked_account_id == LinkedAccount.id)
        .filter(
            Email.source_account != "local-demo",
            Email.is_synced_from_microsoft == True,
            Email.graph_message_id != None,
            LinkedAccount.is_active == True,
        )
        .all()
    )

    updated = 0
    skipped = 0

    for email in emails:
        if email.was_corrected:
            skipped += 1
            continue

        account = email.linked_account
        if not account:
            skipped += 1
            continue

        try:
            access_token = get_valid_microsoft_access_token(db, account=account)
            detail = get_account_message_detail(access_token=access_token, message_id=email.graph_message_id)
            subject = detail.get("subject") or ""
            body = detail.get("body") or ""
            category, confidence = classify_email(subject, body)
            if confidence < CONFIDENCE_THRESHOLD:
                category = "otros"

            email.original_category = category
            email.predicted_category = category
            email.confidence = float(confidence or 0.0)
            email.subject = PRIVACY_SUBJECT_PLACEHOLDER
            email.body = PRIVACY_BODY_PLACEHOLDER
            email.sender = PRIVACY_SENDER_PLACEHOLDER
            updated += 1
        except Exception:
            skipped += 1

    db.commit()
    return {
        "message": "Correos reclasificados sin almacenar contenido del correo",
        "total_updated": updated,
        "total_skipped": skipped,
    }
