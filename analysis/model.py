import logging
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

MODEL_PATH = Path(os.environ.get("MODEL_PATH", "/app/analysis/artifacts/model.pkl"))
ENCODER_PATH = Path(os.environ.get("MODEL_PATH", "/app/analysis/artifacts/model.pkl")).parent / "label_encoder.pkl"
MIN_TRAINING_SAMPLES = 30
RETRAIN_EVERY_N = 50

_model: RandomForestRegressor | None = None
_encoder: LabelEncoder | None = None
_samples_since_last_train: int = 0


def _load_artifacts() -> tuple[RandomForestRegressor | None, LabelEncoder | None]:
    if MODEL_PATH.exists() and ENCODER_PATH.exists():
        try:
            return joblib.load(MODEL_PATH), joblib.load(ENCODER_PATH)
        except Exception as exc:
            logger.warning("Failed to load model artifacts: %s", exc)
    return None, None


def _build_features(
    rows: list[dict], encoder: LabelEncoder | None, fit_encoder: bool = False
) -> np.ndarray:
    categories = [r["category"] for r in rows]
    if fit_encoder or encoder is None:
        enc = LabelEncoder()
        cat_encoded = enc.fit_transform(categories)
    else:
        # Handle unseen categories gracefully
        known = set(encoder.classes_)
        cat_encoded = encoder.transform(
            [c if c in known else encoder.classes_[0] for c in categories]
        )
        enc = encoder

    features = np.column_stack([
        cat_encoded,
        [r["days_active"] for r in rows],
        [r["num_bids"] for r in rows],
        [r["starting_bid"] for r in rows],
    ])
    return features, enc


def train(training_data: list[dict]) -> bool:
    """
    Train the RandomForest on completed auction data.
    Returns True if training succeeded, False if insufficient data.
    """
    global _model, _encoder, _samples_since_last_train

    if len(training_data) < MIN_TRAINING_SAMPLES:
        logger.info(
            "Skipping training — only %d samples (need %d)",
            len(training_data),
            MIN_TRAINING_SAMPLES,
        )
        return False

    X, enc = _build_features(training_data, encoder=None, fit_encoder=True)
    y = np.array([r["final_price"] for r in training_data])

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(enc, ENCODER_PATH)

    _model = model
    _encoder = enc
    _samples_since_last_train = 0
    logger.info("Model trained on %d samples and persisted to %s", len(training_data), MODEL_PATH)
    return True


def predict_value(
    category: str,
    days_active: float,
    num_bids: int,
    starting_bid: float,
) -> float | None:
    """
    Predict estimated final hammer price for an auction.
    Returns None if the model is not trained yet.
    """
    global _model, _encoder

    if _model is None or _encoder is None:
        _model, _encoder = _load_artifacts()

    if _model is None:
        return None

    row = [{"category": category, "days_active": days_active, "num_bids": num_bids, "starting_bid": starting_bid}]
    try:
        X, _ = _build_features(row, encoder=_encoder, fit_encoder=False)
        prediction = float(_model.predict(X)[0])
        return max(prediction, 0.0)
    except Exception as exc:
        logger.warning("Prediction failed: %s", exc)
        return None


def should_retrain(newly_completed: int) -> bool:
    global _samples_since_last_train
    _samples_since_last_train += newly_completed
    return _samples_since_last_train >= RETRAIN_EVERY_N
