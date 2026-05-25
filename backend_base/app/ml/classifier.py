from __future__ import annotations

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


def ensure_model_artifacts() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        train_and_save_demo_model()
        return

    if not FEATURE_CONFIG_PATH.exists():
        joblib.dump({"use_embeddings": False}, FEATURE_CONFIG_PATH)


def load_model_artifacts():
    ensure_model_artifacts()
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)

    if FEATURE_CONFIG_PATH.exists():
        feature_config = joblib.load(FEATURE_CONFIG_PATH)
    else:
        feature_config = {"use_embeddings": False}

    return model, vectorizer, feature_config


def classify_email(subject: str, body: str) -> tuple[str, float]:
    model, vectorizer, feature_config = load_model_artifacts()
    text = preprocess_text(subject, body)

    X = build_hybrid_matrix(
        [text],
        vectorizer=vectorizer,
        fit_vectorizer=False,
        use_embeddings=feature_config.get("use_embeddings", False),
    )

    prediction = model.predict(X)[0]

    if hasattr(model, "predict_proba"):
        confidence = float(max(model.predict_proba(X)[0]))
    else:
        confidence = 0.0

    return prediction, round(confidence, 4)
