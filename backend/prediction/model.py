"""Ensemble ML models for win probability, spread, and totals."""
import math
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from prediction.elo import get_expected_win_prob
from prediction.features import FEATURE_GROUPS, build_feature_row

MODEL_DIR = Path(__file__).resolve().parent.parent / "instance" / "models"
DEFAULT_WEIGHTS = {"elo": 0.40, "stats": 0.40, "schedule": 0.20}
MODEL_FILES = {
    "win_prob": {group: MODEL_DIR / f"win_prob_{group}.pkl" for group in FEATURE_GROUPS},
    "spread": {group: MODEL_DIR / f"spread_{group}.pkl" for group in FEATURE_GROUPS},
    "total": {group: MODEL_DIR / f"total_{group}.pkl" for group in FEATURE_GROUPS},
}


def ensure_model_dir():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _build_regressor() -> Pipeline:
    """Build a standardized linear regression pipeline."""
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("lr", LinearRegression()),
        ]
    )


def _resolve_weights(weights: Optional[Mapping[str, float]] = None) -> Dict[str, float]:
    """Validate manual ensemble weights."""
    raw = weights or DEFAULT_WEIGHTS
    unknown = sorted(set(raw) - set(FEATURE_GROUPS))
    if unknown:
        raise ValueError(f"Unknown weight keys: {', '.join(unknown)}")

    missing = [group for group in FEATURE_GROUPS if group not in raw]
    if missing:
        raise ValueError(f"Missing weight keys: {', '.join(missing)}")

    resolved = {group: float(raw[group]) for group in FEATURE_GROUPS}
    total = sum(resolved.values())
    if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"Ensemble weights must sum to 1.0, got {total:.6f}")
    return resolved


def _fit_classifier(X: np.ndarray, y_win: np.ndarray):
    """Fit a calibrated classifier with a safe cross-validation value."""
    positive_count = int(np.sum(y_win == 1))
    negative_count = int(np.sum(y_win == 0))
    cv = min(5, positive_count, negative_count)
    if cv < 2:
        raise ValueError("Training labels contain fewer than 2 samples for one class")

    clf = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(C=1.0, solver="lbfgs")),
        ]
    )
    calibrated_clf = CalibratedClassifierCV(estimator=clf, method="sigmoid", cv=cv)
    calibrated_clf.fit(X, y_win)
    return calibrated_clf


def train_ensemble_models(
    X_elo: np.ndarray,
    X_stats: np.ndarray,
    X_sched: np.ndarray,
    y_win: np.ndarray,
    y_spread: np.ndarray,
    y_total: np.ndarray,
) -> None:
    """Train and save the ensemble sub-models."""
    ensure_model_dir()

    feature_sets = {
        "elo": X_elo,
        "stats": X_stats,
        "schedule": X_sched,
    }

    for group, X in feature_sets.items():
        joblib.dump(_fit_classifier(X, y_win), MODEL_FILES["win_prob"][group])

        spread_reg = _build_regressor()
        spread_reg.fit(X, y_spread)
        joblib.dump(spread_reg, MODEL_FILES["spread"][group])

        total_reg = _build_regressor()
        total_reg.fit(X, y_total)
        joblib.dump(total_reg, MODEL_FILES["total"][group])


def _predict_group_win_prob(group: str, x: np.ndarray, features: Dict[str, Dict[str, Any]]) -> float:
    """Predict a subset win probability, or use that subset's fallback."""
    model_path = MODEL_FILES["win_prob"][group]
    if model_path.exists():
        clf = joblib.load(model_path)
        return float(clf.predict_proba(x)[0][1])

    if group == "elo":
        return float(get_expected_win_prob(features["elo"]["elo_diff"]))
    return 0.5


def _fallback_margin(group: str, features: Dict[str, Dict[str, Any]]) -> float:
    """Return a heuristic home margin when a spread model is unavailable."""
    if group == "elo":
        return float(features["elo"]["elo_diff"]) / 30.0

    if group == "stats":
        stats = features["stats"]
        avg_pace = (float(stats["home_pace_l10"]) + float(stats["away_pace_l10"])) / 2.0
        return float(stats["net_rating_diff"]) * (avg_pace / 100.0)

    schedule = features["schedule"]
    rest_diff = float(schedule["home_rest_days"]) - float(schedule["away_rest_days"])
    b2b_edge = float(schedule["away_b2b"]) - float(schedule["home_b2b"])
    return (rest_diff * 0.5) + (b2b_edge * 1.5)


def _predict_group_spread(group: str, x: np.ndarray, features: Dict[str, Dict[str, Any]]) -> float:
    """Predict a subset spread, or use that subset's fallback."""
    model_path = MODEL_FILES["spread"][group]
    if model_path.exists():
        reg = joblib.load(model_path)
        margin = float(reg.predict(x)[0])
    else:
        margin = _fallback_margin(group, features)
    return -margin


def _predict_group_total(group: str, x: np.ndarray, features: Dict[str, Dict[str, Any]]) -> float:
    """Predict a subset total, or use that subset's fallback."""
    model_path = MODEL_FILES["total"][group]
    if model_path.exists():
        reg = joblib.load(model_path)
        return float(reg.predict(x)[0])

    if group == "stats":
        stats = features["stats"]
        avg_pace = (float(stats["home_pace_l10"]) + float(stats["away_pace_l10"])) / 2.0
        return max(180.0, min(260.0, avg_pace * 2.25))

    return 225.0


def predict(
    features: Dict[str, Dict[str, Any]],
    weights: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """
    Load ensemble models, score each subset, and return the weighted projection.
    """
    ensure_model_dir()
    resolved_weights = _resolve_weights(weights)

    breakdown: Dict[str, Dict[str, float]] = {}
    for group in FEATURE_GROUPS:
        x = np.array([build_feature_row(features, group)], dtype=float)
        breakdown[group] = {
            "prob": _predict_group_win_prob(group, x, features),
            "spread": _predict_group_spread(group, x, features),
            "total": _predict_group_total(group, x, features),
            "weight": resolved_weights[group],
        }

    final = {
        "home_win_prob": sum(
            breakdown[group]["prob"] * resolved_weights[group] for group in FEATURE_GROUPS
        ),
        "projected_spread": sum(
            breakdown[group]["spread"] * resolved_weights[group] for group in FEATURE_GROUPS
        ),
        "projected_total": sum(
            breakdown[group]["total"] * resolved_weights[group] for group in FEATURE_GROUPS
        ),
    }

    return {
        "final": final,
        "breakdown": breakdown,
    }
