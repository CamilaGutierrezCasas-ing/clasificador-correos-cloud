from collections import Counter
from pathlib import Path
import csv
import re
import unicodedata

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, recall_score, matthews_corrcoef
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from app.models.email import Email
from app.ml.classifier import MODEL_PATH, VECTORIZER_PATH, FEATURE_CONFIG_PATH
from app.ml.features import build_hybrid_matrix, preprocess_text

DATASET_PATH = Path("app/ml/data/dataset_final.csv")

VALID_CATEGORIES = {"urgente", "trabajo", "educacion", "spam", "salud", "otros"}
TRAINABLE_CATEGORIES = {"urgente", "trabajo", "educacion", "spam", "salud", "otros"}
MIN_SAMPLES_PER_CATEGORY = 10

# Déjalo en True para usar embeddings semánticos.
# Si el despliegue se queda sin memoria, puedes ponerlo en False temporalmente.
USE_SEMANTIC_EMBEDDINGS = False


def normalize_category(category: str) -> str:
    value = (category or "").strip().lower()
    value = (
        unicodedata.normalize("NFD", value)
        .encode("ascii", "ignore")
        .decode("utf-8")
    )
    return value


def clean_text(text: str) -> str:
    """
    Limpieza suave.
    No borramos todo el lenguaje natural porque los embeddings semánticos
    necesitan contexto para detectar intención, ironía o frases enredadas.
    """
    text = text or ""
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_csv_dataset():
    texts = []
    labels = []

    if not DATASET_PATH.exists():
        return texts, labels

    with open(DATASET_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            subject = row.get("subject", "")
            body = row.get("body", "")
            category = normalize_category(row.get("category", ""))

            if category not in VALID_CATEGORIES:
                continue

            text = clean_text(preprocess_text(subject, body))

            if len(text) < 10:
                continue

            texts.append(text)
            labels.append(category)

    return texts, labels


def load_db_dataset(db: Session):
    """
    Solo usa correos corregidos manualmente.

    IMPORTANTE:
    Si aplicas privacidad estricta y ya no guardas subject/body de usuarios,
    esta función probablemente devolverá pocos o cero registros. Eso está bien:
    el entrenamiento principal queda basado en el dataset público.
    """
    emails = (
        db.query(Email)
        .filter(
            Email.was_corrected == True,
            Email.source_account != "local-demo",
        )
        .all()
    )

    texts = []
    labels = []

    for e in emails:
        category = normalize_category(e.predicted_category or "")

        if category not in TRAINABLE_CATEGORIES:
            continue

        text = clean_text(preprocess_text(e.subject or "", e.body or ""))

        if len(text) < 10:
            continue

        texts.append(text)
        labels.append(category)

    return texts, labels


def build_confusion_matrix(y_test, y_pred, labels):
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    result = {}

    for i, row_label in enumerate(labels):
        result[row_label] = {}
        for j, col_label in enumerate(labels):
            result[row_label][col_label] = int(cm[i][j])

    return result


def retrain_model_from_all_sources(db: Session) -> dict:
    csv_texts, csv_labels = load_csv_dataset()
    db_texts, db_labels = load_db_dataset(db)

    texts = csv_texts + db_texts
    labels = csv_labels + db_labels

    if len(texts) < 30:
        raise ValueError("No hay suficientes datos para entrenar")

    class_counts = Counter(labels)

    valid_for_split = {
        category: count
        for category, count in class_counts.items()
        if count >= MIN_SAMPLES_PER_CATEGORY
    }

    if len(valid_for_split) < 2:
        raise ValueError(
            "Se necesitan al menos 2 categorías con suficientes correos para entrenar"
        )

    filtered = [
        (text, label)
        for text, label in zip(texts, labels)
        if label in valid_for_split
    ]

    texts = [item[0] for item in filtered]
    labels = [item[1] for item in filtered]

    ordered_labels = sorted(set(labels))

    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.3,
        random_state=42,
        stratify=labels,
    )

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
        max_features=20000,
        min_df=1,
        sublinear_tf=True,
    )

    feature_config = {"use_embeddings": USE_SEMANTIC_EMBEDDINGS}

    X_train_vec = build_hybrid_matrix(
        X_train,
        vectorizer=vectorizer,
        fit_vectorizer=True,
        use_embeddings=feature_config["use_embeddings"],
    )
    X_test_vec = build_hybrid_matrix(
        X_test,
        vectorizer=vectorizer,
        fit_vectorizer=False,
        use_embeddings=feature_config["use_embeddings"],
    )

    model = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        solver="liblinear",
    )

    model.fit(X_train_vec, y_train)

    y_pred = model.predict(X_test_vec)

    accuracy = accuracy_score(y_test, y_pred)
    recall_macro = recall_score(
        y_test,
        y_pred,
        average="macro",
        zero_division=0,
    )
    mcc_multiclass = matthews_corrcoef(y_test, y_pred)

    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(feature_config, FEATURE_CONFIG_PATH)

    return {
        "message": "Modelo entrenado: Logistic Regression + TF-IDF n-gramas + meta-features",
        "total_samples": len(texts),
        "csv_samples": len(csv_texts),
        "db_corrected_samples": len(db_texts),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": round(float(accuracy), 4),
        "recall_macro": round(float(recall_macro), 4),
        "mcc_multiclass": round(float(mcc_multiclass), 4),
        "feature_strategy": feature_config,
        "categories": dict(Counter(labels)),
        "confusion_matrix": build_confusion_matrix(
            y_test,
            y_pred,
            ordered_labels,
        ),
    }
