from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from app.ml.features import build_hybrid_matrix, preprocess_text

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "logistic_model.joblib"
VECTORIZER_PATH = ARTIFACTS_DIR / "tfidf_vectorizer.joblib"
FEATURE_CONFIG_PATH = ARTIFACTS_DIR / "feature_config.joblib"

MODEL_VERSION = "fase4-logistic-tfidf-ngram-meta-embeddings-v1"


def _demo_training_data() -> tuple[list[str], list[str]]:
    samples = [
        ("pago pendiente urgente responder hoy", "urgente"),
        ("reunion importante a primera hora con gerencia", "urgente"),
        ("entrega informe laboral proyecto cliente", "trabajo"),
        ("cronograma reunion oficina y tareas del equipo", "trabajo"),
        ("matricula semestre examen docente aula universidad", "educacion"),
        ("actividad academica estudiante curso plataforma", "educacion"),
        ("cita medica eps resultados laboratorio formula", "salud"),
        ("control medico incapacidad tratamiento y salud", "salud"),
        ("gana dinero oferta promocion haz clic premio", "spam"),
        ("descuento gratis compra ahora publicidad", "spam"),
        ("feliz cumpleanos fotos del fin de semana", "otros"),
        ("invitacion almuerzo familia y saludo", "otros"),
    ]
    texts = [t for t, _ in samples]
    labels = [y for _, y in samples]
    return texts, labels


def train_and_save_demo_model() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    texts, labels = _demo_training_data()

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
        max_features=20000,
        min_df=1,
        sublinear_tf=True,
    )

    feature_config = {"use_embeddings": False}
    X = build_hybrid_matrix(
        texts,
        vectorizer=vectorizer,
        fit_vectorizer=True,
        use_embeddings=feature_config["use_embeddings"],
    )

    model = LogisticRegression(max_iter=2000, class_weight="balanced")
    model.fit(X, labels)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(feature_config, FEATURE_CONFIG_PATH)
    clear_model_cache()


def ensure_model_artifacts() -> None:
    if (
        not MODEL_PATH.exists()
        or not VECTORIZER_PATH.exists()
        or not FEATURE_CONFIG_PATH.exists()
    ):
        train_and_save_demo_model()


@lru_cache(maxsize=1)
def _load_model_artifacts_cached():
    """
    Carga modelo/vectorizador una sola vez por proceso.

    Antes se cargaban los archivos joblib en cada correo. Con 1000 correos por
    cuenta eso hacía 1000 lecturas de disco y era una de las principales causas
    de lentitud.
    """
    ensure_model_artifacts()
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)

    if FEATURE_CONFIG_PATH.exists():
        feature_config = joblib.load(FEATURE_CONFIG_PATH)
    else:
        feature_config = {"use_embeddings": False}

    return model, vectorizer, feature_config


def load_model_artifacts():
    return _load_model_artifacts_cached()


def clear_model_cache() -> None:
    """Limpia caché después de reentrenar para usar el modelo nuevo."""
    _load_model_artifacts_cached.cache_clear()


def classify_emails_batch(email_pairs: list[tuple[str, str]]) -> list[tuple[str, float]]:
    """
    Clasifica muchos correos en una sola llamada.

    Entrada: [(subject, body_preview), ...]
    Salida: [(category, confidence), ...]
    """
    if not email_pairs:
        return []

    model, vectorizer, feature_config = load_model_artifacts()
    texts = [preprocess_text(subject, body) for subject, body in email_pairs]

    X = build_hybrid_matrix(
        texts,
        vectorizer=vectorizer,
        fit_vectorizer=False,
        use_embeddings=feature_config.get("use_embeddings", False),
    )

    predictions = model.predict(X)

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X)
        confidences = [float(max(row)) for row in probabilities]
    else:
        confidences = [0.0 for _ in predictions]

    return [
        (str(category), round(float(confidence), 4))
        for category, confidence in zip(predictions, confidences)
    ]


def classify_email(subject: str, body: str) -> tuple[str, float]:
    result = classify_emails_batch([(subject, body)])
    if not result:
        return "otros", 0.0
    return result[0]
