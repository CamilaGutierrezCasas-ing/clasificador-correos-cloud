from __future__ import annotations

from functools import lru_cache
import re
from typing import Iterable

import numpy as np
from scipy.sparse import csr_matrix, hstack


SEMANTIC_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def preprocess_text(subject: str, body: str) -> str:
    """
    Une asunto + cuerpo. No elimina todo el contexto porque los embeddings
    necesitan frases completas para entender mejor la intención.
    """
    subject = subject or ""
    body = body or ""
    return f"{subject} {body}".strip()


def extract_meta_features(text: str) -> list[float]:
    """
    Señales estructurales del correo.
    Ayudan a detectar spam, urgencia y mensajes atípicos.
    """
    original = text or ""
    lower = original.lower()

    length = len(original)
    word_count = len(original.split())
    exclamation_count = original.count("!")
    question_count = original.count("?")
    digit_count = sum(char.isdigit() for char in original)
    link_count = len(re.findall(r"http\S+|www\S+", original))
    email_count = len(re.findall(r"\S+@\S+", original))
    uppercase_ratio = sum(char.isupper() for char in original) / max(len(original), 1)

    money_words = int(any(
        word in lower
        for word in [
            "money", "payment", "invoice", "bank", "prize", "discount", "free",
            "pago", "factura", "banco", "premio", "descuento", "gratis",
        ]
    ))

    urgent_words = int(any(
        word in lower
        for word in [
            "urgent", "asap", "important", "deadline", "today", "now",
            "urgente", "importante", "plazo", "hoy", "ahora", "inmediato",
        ]
    ))

    education_words = int(any(
        word in lower
        for word in [
            "class", "course", "teacher", "student", "homework", "exam",
            "clase", "curso", "docente", "estudiante", "tarea", "examen",
            "universidad", "colegio",
        ]
    ))

    health_words = int(any(
        word in lower
        for word in [
            "health", "doctor", "medical", "appointment", "hospital", "medicine",
            "salud", "medico", "médico", "cita", "hospital", "medicina", "eps",
        ]
    ))

    return [
        float(length),
        float(word_count),
        float(exclamation_count),
        float(question_count),
        float(digit_count),
        float(link_count),
        float(email_count),
        float(uppercase_ratio),
        
    ]


def build_meta_matrix(texts: Iterable[str]) -> csr_matrix:
    return csr_matrix([extract_meta_features(text) for text in texts], dtype=float)


@lru_cache(maxsize=1)
def get_embedding_model():
    """
    Carga el modelo semántico una sola vez.
    Requiere instalar: sentence-transformers
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(SEMANTIC_MODEL_NAME)


def build_embedding_matrix(texts: list[str]) -> csr_matrix:
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return csr_matrix(np.asarray(embeddings, dtype=np.float32))


def build_hybrid_matrix(
    texts: list[str],
    *,
    vectorizer,
    fit_vectorizer: bool = False,
    use_embeddings: bool = True,
):
    """
    Une:
    1. TF-IDF con n-gramas
    2. Meta-features
    3. Embeddings semánticos

    Esta es la representación híbrida que entra a Logistic Regression.
    """
    if fit_vectorizer:
        tfidf_matrix = vectorizer.fit_transform(texts)
    else:
        tfidf_matrix = vectorizer.transform(texts)

    meta_matrix = build_meta_matrix(texts)

    if use_embeddings:
        embedding_matrix = build_embedding_matrix(texts)
        return hstack([tfidf_matrix, meta_matrix, embedding_matrix]).tocsr()

    return hstack([tfidf_matrix, meta_matrix]).tocsr()
