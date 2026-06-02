from __future__ import annotations

import re
from urllib.parse import urlparse


def _clean(value: str | None) -> str:
    return (value or "").strip().lower()


def _domain_from_sender(sender: str | None) -> str:
    text = _clean(sender)
    if "@" in text:
        return text.split("@", 1)[1].strip()

    # Por si alguna vez llega un dominio/URL en lugar de correo.
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        return (parsed.netloc or "").lower()

    return text


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _bump_confidence(confidence: float, minimum: float) -> float:
    """Sube ligeramente la confianza cuando una regla de remitente es fuerte."""
    try:
        value = float(confidence or 0.0)
    except Exception:
        value = 0.0
    return round(max(value, minimum), 4)


def apply_sender_context_rules(
    *,
    sender: str | None,
    subject: str | None,
    body_preview: str | None,
    category: str,
    confidence: float,
) -> tuple[str, float]:
    """
    Mejora la categoría usando remitente/dominio SOLO en memoria.

    Importante para privacidad:
    - Esta función NO guarda remitente, asunto ni contenido.
    - Solo usa esas señales temporalmente durante la clasificación.
    - Lo que se persiste en BD sigue siendo metadato: categoría/confianza/id.
    """
    domain = _domain_from_sender(sender)
    text = f"{_clean(subject)} {_clean(body_preview)} {domain}"
    category = _clean(category) or "otros"

    # 1) LinkedIn: no todo LinkedIn es trabajo. Se discrimina por intención.
    linkedin_domains = ["linkedin.com", "linkedinmail.com", "e.linkedin.com"]
    linkedin_job_words = [
        "vacante", "empleo", "job", "jobs", "hiring", "recruiter", "reclutador",
        "candidatura", "aplicación", "application", "entrevista", "interview",
        "puesto", "position", "talent", "career", "carrera profesional",
        "te busca", "ha visto tu perfil", "oportunidad laboral",
    ]
    linkedin_learning_words = [
        "learning", "curso", "courses", "certificado", "certificate", "aprendizaje",
        "formación", "formacion", "clase", "lección", "lesson",
    ]
    linkedin_promo_words = [
        "premium", "promoción", "promocion", "descuento", "offer", "oferta", "trial",
        "prueba gratis", "ads", "anuncio",
    ]

    if any(d in domain for d in linkedin_domains):
        if _contains_any(text, linkedin_job_words):
            return "trabajo", _bump_confidence(confidence, 0.78)
        if _contains_any(text, linkedin_learning_words):
            return "educacion", _bump_confidence(confidence, 0.72)
        if _contains_any(text, linkedin_promo_words):
            return "spam", _bump_confidence(confidence, 0.70)
        # LinkedIn sin señal clara: mantener predicción del modelo.
        return category, confidence

    # 2) Plataformas de empleo / reclutamiento.
    work_domains = [
        "computrabajo", "elempleo", "indeed", "glassdoor", "magneto365",
        "greenhouse.io", "lever.co", "workday", "smartrecruiters", "bumeran",
        "talent.com", "hire", "recruit", "recruiting",
    ]
    work_words = [
        "vacante", "empleo", "postulación", "postulacion", "candidatura", "entrevista",
        "hoja de vida", "curriculum", "cv", "recruiter", "oferta laboral", "proceso de selección",
        "proceso de seleccion", "contratación", "contratacion", "puesto", "cargo",
    ]
    if _contains_any(domain, work_domains) or _contains_any(text, work_words):
        return "trabajo", _bump_confidence(confidence, 0.74)

    # 3) Educación: universidades y plataformas académicas.
    education_domains = [
        ".edu", ".edu.co", "universidad", "university", "moodle", "canvas",
        "blackboard", "coursera", "edx", "udemy", "platzi", "duolingo",
        "classroom", "academia", "campus",
    ]
    education_words = [
        "matrícula", "matricula", "clase", "curso", "examen", "quiz", "tarea",
        "estudiante", "docente", "profesor", "semestre", "aula", "calificación",
        "calificacion", "certificado", "diploma", "inscripción", "inscripcion",
    ]
    if _contains_any(domain, education_domains) or _contains_any(text, education_words):
        return "educacion", _bump_confidence(confidence, 0.72)

    # 4) Salud: EPS, laboratorios, citas y clínicas.
    health_domains = [
        "eps", "salud", "clinic", "clinica", "hospital", "laboratorio", "medical",
        "medico", "médico", "sanitas", "sura", "compensar", "famisanar", "colsanitas",
    ]
    health_words = [
        "cita médica", "cita medica", "resultado", "laboratorio", "examen médico",
        "examen medico", "historia clínica", "historia clinica", "incapacidad",
        "fórmula", "formula", "medicamento", "paciente", "consulta médica",
    ]
    if _contains_any(domain, health_domains) or _contains_any(text, health_words):
        return "salud", _bump_confidence(confidence, 0.74)

    # 5) Spam/promocional: usar con cuidado para no mandar notificaciones reales a spam.
    spam_domains = [
        "newsletter", "marketing", "promotions", "promociones", "mailchimp", "sendgrid",
        "salesforce", "hubspot", "campaign", "publicidad",
    ]
    spam_words = [
        "descuento", "promoción", "promocion", "compra ahora", "oferta exclusiva",
        "gratis", "gana", "premio", "cupón", "cupon", "2x1", "black friday",
        "cyber", "rebaja", "última oportunidad", "ultima oportunidad",
    ]
    if _contains_any(domain, spam_domains) or _contains_any(text, spam_words):
        return "spam", _bump_confidence(confidence, 0.70)

    # 6) Urgente: palabras de acción inmediata.
    urgent_words = [
        "urgente", "hoy", "inmediato", "vencido", "vence", "último aviso", "ultimo aviso",
        "acción requerida", "accion requerida", "bloqueo", "suspendida", "suspendido",
        "pago pendiente", "requiere atención", "requiere atencion",
    ]
    if _contains_any(text, urgent_words):
        return "urgente", _bump_confidence(confidence, 0.72)

    return category, round(float(confidence or 0.0), 4)
