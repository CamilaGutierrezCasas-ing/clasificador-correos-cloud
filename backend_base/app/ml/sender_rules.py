from __future__ import annotations

from urllib.parse import urlparse


def _clean(value: str | None) -> str:
    return (value or "").strip().lower()


def _domain_from_sender(sender: str | None) -> str:
    text = _clean(sender)
    if "@" in text:
        return text.split("@", 1)[1].strip()

    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        return (parsed.netloc or "").lower()

    return text


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _bump_confidence(confidence: float, minimum: float) -> float:
    """Eleva la confianza cuando existe una señal contextual fuerte.

    No inventa contenido ni guarda datos sensibles. Solo ajusta el score final
    de clasificación cuando el remitente/dominio y el texto temporal apuntan
    claramente a una categoría.
    """
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

    Privacidad:
    - NO guarda remitente.
    - NO guarda asunto.
    - NO guarda body/bodyPreview.
    - Solo retorna categoría y confianza final para persistir metadatos.
    """
    domain = _domain_from_sender(sender)
    text = f"{_clean(subject)} {_clean(body_preview)} {domain}"
    category = _clean(category) or "otros"

    # LinkedIn: separar empleo, educación y promoción.
    linkedin_domains = ["linkedin.com", "linkedinmail.com", "e.linkedin.com"]
    linkedin_job_words = [
        "vacante", "empleo", "job", "jobs", "hiring", "recruiter", "reclutador",
        "candidatura", "aplicación", "aplicacion", "application", "entrevista",
        "interview", "puesto", "position", "talent", "career", "carrera profesional",
        "te busca", "ha visto tu perfil", "oportunidad laboral", "analista", "ingeniero",
        "developer", "desarrollador", "intern", "pasantía", "pasantia", "práctica",
        "practica", "selección", "seleccion", "contratación", "contratacion",
    ]
    linkedin_learning_words = [
        "learning", "curso", "courses", "certificado", "certificate", "aprendizaje",
        "formación", "formacion", "clase", "lección", "lesson", "skill", "skills",
    ]
    linkedin_promo_words = [
        "premium", "promoción", "promocion", "descuento", "offer", "oferta", "trial",
        "prueba gratis", "ads", "anuncio", "advertising",
    ]

    if any(d in domain for d in linkedin_domains):
        if _contains_any(text, linkedin_job_words):
            return "trabajo", _bump_confidence(confidence, 0.88)
        if _contains_any(text, linkedin_learning_words):
            return "educacion", _bump_confidence(confidence, 0.84)
        if _contains_any(text, linkedin_promo_words):
            return "spam", _bump_confidence(confidence, 0.82)
        return category, _bump_confidence(confidence, 0.45)

    # Plataformas de empleo/reclutamiento.
    work_domains = [
        "computrabajo", "elempleo", "indeed", "glassdoor", "magneto365",
        "greenhouse.io", "lever.co", "workday", "smartrecruiters", "bumeran",
        "talent.com", "hire", "recruit", "recruiting", "job", "jobs",
    ]
    work_words = [
        "vacante", "empleo", "postulación", "postulacion", "candidatura", "entrevista",
        "hoja de vida", "curriculum", "cv", "recruiter", "oferta laboral",
        "proceso de selección", "proceso de seleccion", "contratación", "contratacion",
        "puesto", "cargo", "seleccionado", "aplicar", "apply", "hiring",
    ]
    if _contains_any(domain, work_domains) or _contains_any(text, work_words):
        return "trabajo", _bump_confidence(confidence, 0.86)

    # Educación.
    education_domains = [
        ".edu", ".edu.co", "universidad", "university", "moodle", "canvas",
        "blackboard", "coursera", "edx", "udemy", "platzi", "duolingo",
        "classroom", "academia", "campus", "school", "colegio",
    ]
    education_words = [
        "matrícula", "matricula", "clase", "curso", "examen", "quiz", "tarea",
        "estudiante", "docente", "profesor", "semestre", "aula", "calificación",
        "calificacion", "certificado", "diploma", "inscripción", "inscripcion",
        "universidad", "materia", "actividad académica", "actividad academica",
    ]
    if _contains_any(domain, education_domains) or _contains_any(text, education_words):
        return "educacion", _bump_confidence(confidence, 0.84)

    # Salud.
    health_domains = [
        "eps", "salud", "clinic", "clinica", "hospital", "laboratorio", "medical",
        "medico", "médico", "sanitas", "sura", "compensar", "famisanar", "colsanitas",
    ]
    health_words = [
        "cita médica", "cita medica", "resultado", "laboratorio", "examen médico",
        "examen medico", "historia clínica", "historia clinica", "incapacidad",
        "fórmula", "formula", "medicamento", "paciente", "consulta médica",
        "vacunación", "vacunacion", "covid", "odontología", "odontologia",
    ]
    if _contains_any(domain, health_domains) or _contains_any(text, health_words):
        return "salud", _bump_confidence(confidence, 0.86)

    # Spam/promocional.
    spam_domains = [
        "newsletter", "marketing", "promotions", "promociones", "mailchimp", "sendgrid",
        "salesforce", "hubspot", "campaign", "publicidad", "promo",
    ]
    spam_words = [
        "descuento", "promoción", "promocion", "compra ahora", "oferta exclusiva",
        "gratis", "gana", "premio", "cupón", "cupon", "2x1", "black friday",
        "cyber", "rebaja", "última oportunidad", "ultima oportunidad", "aprovecha",
    ]
    if _contains_any(domain, spam_domains) or _contains_any(text, spam_words):
        return "spam", _bump_confidence(confidence, 0.82)

    # Urgente.
    urgent_words = [
        "urgente", "hoy", "inmediato", "vencido", "vence", "último aviso", "ultimo aviso",
        "acción requerida", "accion requerida", "bloqueo", "suspendida", "suspendido",
        "pago pendiente", "requiere atención", "requiere atencion", "importante", "alerta",
    ]
    if _contains_any(text, urgent_words):
        return "urgente", _bump_confidence(confidence, 0.84)

    return category, round(float(confidence or 0.0), 4)
