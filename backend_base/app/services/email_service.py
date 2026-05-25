from datetime import datetime
from collections import Counter, defaultdict

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ml.classifier import classify_email
from app.models.email import Email
from app.models.linked_account import LinkedAccount
from app.models.user import User
from app.services.microsoft_graph_service import get_account_messages

CONFIDENCE_THRESHOLD = 0.15
LOW_CONFIDENCE_STATS_THRESHOLD = 0.20


PRIVACY_SUBJECT_PLACEHOLDER = "[Contenido no almacenado por privacidad]"
PRIVACY_BODY_PLACEHOLDER = ""
PRIVACY_SENDER_PLACEHOLDER = "[Remitente no almacenado]"


def mask_email_address(value: str) -> str:
    """
    Evita guardar el correo completo del remitente.
    Conserva solo el dominio para análisis básico, por ejemplo: *@empresa.com
    """
    value = (value or "").strip()
    if "@" not in value:
        return PRIVACY_SENDER_PLACEHOLDER

    domain = value.split("@", 1)[1].strip()
    if not domain:
        return PRIVACY_SENDER_PLACEHOLDER

    return f"*@{domain}"



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
    original_subject = (subject or "").strip()
    original_body = (body or "").strip()
    original_sender = (sender or "desconocido").strip()

    # Privacidad por diseño:
    # por defecto NO se guarda el contenido real del correo del usuario.
    if store_content:
        subject = original_subject
        body = original_body
        sender = original_sender
    else:
        subject = PRIVACY_SUBJECT_PLACEHOLDER
        body = PRIVACY_BODY_PLACEHOLDER
        sender = mask_email_address(original_sender)

    source_account = (source_account or "local-demo").strip()
    predicted_category = (predicted_category or "otros").strip().lower()

    email = Email(
        owner_user_id=owner.id,
        linked_account_id=linked_account_id,
        graph_message_id=graph_message_id,
        subject=subject,
        body=body,
        sender=sender,
        source_account=source_account,
        original_category=predicted_category,
        predicted_category=predicted_category,
        confidence=confidence,
        was_corrected=False,
        is_synced_from_microsoft=is_synced_from_microsoft,
        received_at=received_at or datetime.utcnow(),
    )
    db.add(email)
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
    category = (category or "").strip().lower()

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


def get_email_by_graph_message_id(
    db: Session,
    *,
    graph_message_id: str,
) -> Email | None:
    return (
        db.query(Email)
        .filter(Email.graph_message_id == graph_message_id)
        .first()
    )


def update_email_category(
    db: Session,
    *,
    owner: User,
    email_id: int,
    new_category: str,
) -> Email | None:
    new_category = (new_category or "otros").strip().lower()

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

    if email.predicted_category != new_category:
        email.predicted_category = new_category
        email.was_corrected = True

    db.commit()
    db.refresh(email)

    return email


def sync_emails_from_microsoft_account(
    db: Session,
    *,
    owner: User,
    account: LinkedAccount,
    top: int = 200,
) -> list[Email]:
    messages = get_account_messages(access_token=account.access_token, top=top)
    saved_emails: list[Email] = []

    for msg in messages:
        graph_message_id = msg.get("id")
        if not graph_message_id:
            continue

        existing = get_email_by_graph_message_id(
            db,
            graph_message_id=graph_message_id,
        )
        if existing:
            continue

        subject = msg.get("subject") or ""
        body = msg.get("bodyPreview") or ""

        from_data = msg.get("from", {})
        email_address = from_data.get("emailAddress", {})
        sender = email_address.get("address") or "desconocido"

        received_raw = msg.get("receivedDateTime")
        received_at = None
        if received_raw:
            try:
                received_at = datetime.fromisoformat(received_raw.replace("Z", "+00:00"))
            except Exception:
                received_at = None

        category, confidence = classify_email(subject, body)

        if confidence < CONFIDENCE_THRESHOLD:
            category = "otros"

        email = create_classified_email(
            db,
            owner=owner,
            subject=subject,
            body=body,
            sender=sender,
            source_account=account.account_email,
            predicted_category=category,
            confidence=confidence,
            linked_account_id=account.id,
            graph_message_id=graph_message_id,
            is_synced_from_microsoft=True,
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

    total = len(emails)

    if total == 0:
        return {
            "total_emails": 0,
            "by_category": {},
            "average_confidence": 0,
            "low_confidence_count": 0,
            "manual_corrections": 0,
            "confusion_matrix": {},
        }

    categories = [e.predicted_category for e in emails if e.predicted_category]
    category_counts = Counter(categories)

    avg_conf = sum((e.confidence or 0.0) for e in emails) / total

    low_conf = len([
        e for e in emails
        if (e.confidence or 0.0) < LOW_CONFIDENCE_STATS_THRESHOLD
    ])

    corrected = len([e for e in emails if e.was_corrected])

    matrix = defaultdict(lambda: defaultdict(int))

    for e in emails:
        original = (e.original_category or "sin_dato").lower()
        final = (e.predicted_category or "sin_dato").lower()
        matrix[original][final] += 1

    return {
        "total_emails": total,
        "by_category": dict(category_counts),
        "average_confidence": round(avg_conf, 4),
        "low_confidence_count": low_conf,
        "manual_corrections": corrected,
        "confusion_matrix": {k: dict(v) for k, v in matrix.items()},
    }


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

    total = len(emails)

    if total == 0:
        return {
            "total_emails": 0,
            "by_category": {},
            "by_account": {},
            "by_user": {},
            "average_confidence": 0,
            "low_confidence_count": 0,
            "manual_corrections": 0,
            "confusion_matrix": {},
        }

    categories = [e.predicted_category for e in emails if e.predicted_category]
    category_counts = Counter(categories)

    accounts = [e.source_account for e in emails if e.source_account]
    account_counts = Counter(accounts)

    users = [e.owner_user_id for e in emails if e.owner_user_id is not None]
    user_counts = Counter(users)

    avg_conf = sum((e.confidence or 0.0) for e in emails) / total

    low_conf = len([
        e for e in emails
        if (e.confidence or 0.0) < LOW_CONFIDENCE_STATS_THRESHOLD
    ])

    corrected = len([e for e in emails if e.was_corrected])

    matrix = defaultdict(lambda: defaultdict(int))

    for e in emails:
        original = (e.original_category or "sin_dato").lower()
        final = (e.predicted_category or "sin_dato").lower()
        matrix[original][final] += 1

    return {
        "total_emails": total,
        "by_category": dict(category_counts),
        "by_account": dict(account_counts),
        "by_user": dict(user_counts),
        "average_confidence": round(avg_conf, 4),
        "low_confidence_count": low_conf,
        "manual_corrections": corrected,
        "confusion_matrix": {k: dict(v) for k, v in matrix.items()},
    }


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
        "resume",
        "resumir",
        "resumen",
        "mostrar",
        "muestrame",
        "muéstrame",
        "buscar",
        "busca",
        "que",
        "qué",
        "tengo",
        "mis",
        "correos",
        "de",
        "del",
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

    if filters.get("sender_contains"):
        sender_value = f"%{filters['sender_contains']}%"
        query = query.filter(Email.sender.ilike(sender_value))

    if filters.get("text_contains"):
        text_value = f"%{filters['text_contains']}%"
        query = query.filter(
            or_(
                Email.subject.ilike(text_value),
                Email.body.ilike(text_value),
            )
        )

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

    top_subjects = [e.subject for e in emails[:3] if e.subject]
    if top_subjects:
        summary += " Algunos asuntos encontrados son: " + "; ".join(top_subjects) + "."

    return summary


def chatbot_email_query(
    db: Session,
    *,
    owner: User,
    user_query: str,
) -> dict:
    intent, filters = parse_chatbot_query(user_query)
    emails = search_emails_for_chatbot(
        db,
        owner=owner,
        filters=filters,
        limit=10,
    )
    summary = build_chatbot_summary(filters, emails)

    return {
        "intent": intent,
        "applied_filters": filters,
        "total_results": len(emails),
        "summary": summary,
        "emails": emails,
    }

def reclassify_all_emails(db: Session):
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

    updated = 0

    for email in emails:
        subject = email.subject or ""
        body = email.body or ""

        if not subject and not body:
            continue

        email.original_category = email.predicted_category or "sin_dato"

        category, confidence = classify_email(subject, body)

        email.predicted_category = category
        email.confidence = confidence

        updated += 1

    db.commit()

    return {
        "message": "Correos reclasificados correctamente",
        "total_updated": updated,
    }