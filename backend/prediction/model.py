"""Consolidated XGBoost models for win probability, spread, and totals."""
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import joblib
import numpy as np
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from prediction.features import CONSOLIDATED_FEATURES, build_feature_row

MODEL_DIR = Path(__file__).resolve().parent.parent / "instance" / "models"
MODEL_FILES = {
    "win_prob": MODEL_DIR / "win_prob.pkl",
    "spread": MODEL_DIR / "spread.pkl",
    "total": MODEL_DIR / "total.pkl",
}
RANDOM_STATE = 42
MODEL_N_JOBS = int(os.environ.get("MODEL_TRAIN_N_JOBS", "1"))
GRID_N_JOBS = int(os.environ.get("MODEL_GRID_N_JOBS", "1"))
CLASSIFIER_PARAM_GRID = {
    "xgb__max_depth": [3, 4, 5],
    "xgb__learning_rate": [0.03, 0.05, 0.1],
    "xgb__n_estimators": [120, 200, 300],
    "xgb__subsample": [0.8, 1.0],
    "xgb__colsample_bytree": [0.8, 1.0],
}
REGRESSOR_PARAM_GRID = {
    "xgb__max_depth": [3, 4, 5],
    "xgb__learning_rate": [0.03, 0.05, 0.1],
    "xgb__n_estimators": [120, 200, 300],
    "xgb__subsample": [0.8, 1.0],
    "xgb__colsample_bytree": [0.8, 1.0],
}
DEFAULT_TOP_FEATURES = 5


def ensure_model_dir() -> None:
    """Ensure the model output directory exists."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _build_classifier_pipeline() -> Pipeline:
    """Construct the consolidated binary classifier pipeline."""
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "xgb",
                XGBClassifier(
                    objective="binary:logistic",
                    eval_metric="logloss",
                    random_state=RANDOM_STATE,
                    n_jobs=MODEL_N_JOBS,
                    verbosity=0,
                ),
            ),
        ]
    )


def _build_regressor_pipeline() -> Pipeline:
    """Construct the consolidated regression pipeline."""
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "xgb",
                XGBRegressor(
                    objective="reg:squarederror",
                    random_state=RANDOM_STATE,
                    n_jobs=MODEL_N_JOBS,
                    verbosity=0,
                ),
            ),
        ]
    )


def _fit_random_search(
    estimator,
    param_grid: Mapping[str, List[Any]],
    X: np.ndarray,
    y: np.ndarray,
    scoring: str,
    cv: int,
) -> GridSearchCV:
    """Run a grid search and return the fitted search object."""
    search = GridSearchCV(
        estimator=estimator,
        param_grid=param_grid,
        scoring=scoring,
        cv=cv,
        n_jobs=GRID_N_JOBS,
        refit=True,
        error_score="raise",
    )
    search.fit(X, y)
    return search


def _resolve_classifier_cv(y_win: np.ndarray) -> int:
    """Return a safe cross-validation fold count for classification."""
    positive_count = int(np.sum(y_win == 1))
    negative_count = int(np.sum(y_win == 0))
    cv = min(5, positive_count, negative_count)
    if cv < 2:
        raise ValueError("Training labels contain fewer than 2 samples for one class")
    return cv


def _resolve_regressor_cv(y: np.ndarray) -> int:
    """Return a safe cross-validation fold count for regression."""
    cv = min(5, len(y))
    if cv < 2:
        raise ValueError("Regression training requires at least 2 samples")
    return cv


def _fit_classifier(X: np.ndarray, y_win: np.ndarray) -> Dict[str, Any]:
    """Fit a tuned XGBoost classifier with cross-validation."""
    cv = _resolve_classifier_cv(y_win)
    search = _fit_random_search(
        estimator=_build_classifier_pipeline(),
        param_grid=CLASSIFIER_PARAM_GRID,
        X=X,
        y=y_win,
        scoring="neg_log_loss",
        cv=cv,
    )
    return {
        "estimator": search.best_estimator_,
        "best_params": search.best_params_,
        "best_score": float(search.best_score_),
        "cv": cv,
    }


def _fit_regressor(X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """Fit a tuned XGBoost regressor with cross-validation."""
    cv = _resolve_regressor_cv(y)
    search = _fit_random_search(
        estimator=_build_regressor_pipeline(),
        param_grid=REGRESSOR_PARAM_GRID,
        X=X,
        y=y,
        scoring="neg_mean_squared_error",
        cv=cv,
    )
    return {
        "estimator": search.best_estimator_,
        "best_params": search.best_params_,
        "best_score": float(search.best_score_),
        "cv": cv,
    }


def train_consolidated_models(
    X: np.ndarray,
    y_win: np.ndarray,
    y_spread: np.ndarray,
    y_total: np.ndarray,
) -> Dict[str, Dict[str, Any]]:
    """Train, tune, and save consolidated models."""
    ensure_model_dir()

    win_result = _fit_classifier(X, y_win)
    spread_result = _fit_regressor(X, y_spread)
    total_result = _fit_regressor(X, y_total)

    results = {
        "win_prob": win_result,
        "spread": spread_result,
        "total": total_result,
    }

    for model_name, result in results.items():
        estimator = result["estimator"]
        setattr(estimator, "feature_names_", list(CONSOLIDATED_FEATURES))
        joblib.dump(estimator, MODEL_FILES[model_name])

    return {
        model_name: {
            "best_params": result["best_params"],
            "best_score": result["best_score"],
            "cv": result["cv"],
        }
        for model_name, result in results.items()
    }


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a value into a closed interval."""
    return max(low, min(high, value))


def _sigmoid(value: float) -> float:
    """Stable logistic transform."""
    return 1.0 / (1.0 + math.exp(-float(value)))


def _feature_map(features: Mapping[str, Any]) -> Dict[str, float]:
    """Normalize an arbitrary feature mapping into the consolidated schema."""
    return {
        feature_name: float(features.get(feature_name, 0.0) or 0.0)
        for feature_name in CONSOLIDATED_FEATURES
    }


def _load_model(model_name: str):
    """Load one persisted model if it exists."""
    model_path = MODEL_FILES[model_name]
    if not model_path.exists():
        return None
    return joblib.load(model_path)


def _fallback_feature_contributions(features: Mapping[str, float]) -> Dict[str, float]:
    """Approximate win-probability drivers when trained models are absent."""
    return {
        "elo_diff": float(features["elo_diff"]) / 180.0,
        "net_rating_diff": float(features["net_rating_diff"]) / 9.0,
        "home_rest_days": float(features["home_rest_days"]) * 0.02,
        "away_rest_days": float(features["away_rest_days"]) * -0.02,
        "home_b2b": float(features["home_b2b"]) * -0.18,
        "away_b2b": float(features["away_b2b"]) * 0.18,
        "home_distance_traveled": float(features["home_distance_traveled"]) / -2600.0,
        "away_distance_traveled": float(features["away_distance_traveled"]) / 2600.0,
        "home_injury_impact": float(features["home_injury_impact"]) * 0.9,
        "away_injury_impact": float(features["away_injury_impact"]) * -0.9,
        "ref_home_bias": float(features["ref_home_bias"]) * 0.35,
        "ref_total_bias": float(features["ref_total_bias"]) * 0.05,
        "ref_foul_bias": float(features["ref_foul_bias"]) * 0.05,
        "home_pace_l10": float(features["home_pace_l10"]) * 0.002,
        "away_pace_l10": float(features["away_pace_l10"]) * -0.002,
        "home_net_rating_l10": float(features["home_net_rating_l10"]) * 0.015,
        "away_net_rating_l10": float(features["away_net_rating_l10"]) * -0.015,
    }


def _fallback_home_win_prob(features: Mapping[str, float]) -> float:
    """Heuristic home win probability when the trained classifier is unavailable."""
    signal = sum(_fallback_feature_contributions(features).values())
    return _clamp(_sigmoid(signal), 0.05, 0.95)


def _fallback_margin(features: Mapping[str, float]) -> float:
    """Heuristic home margin when the spread regressor is unavailable."""
    avg_pace = (float(features["home_pace_l10"]) + float(features["away_pace_l10"])) / 2.0
    return (
        (float(features["elo_diff"]) / 28.0)
        + (float(features["net_rating_diff"]) * (avg_pace / 100.0) * 0.75)
        + ((float(features["home_rest_days"]) - float(features["away_rest_days"])) * 0.45)
        + ((float(features["away_b2b"]) - float(features["home_b2b"])) * 1.25)
        + ((float(features["away_distance_traveled"]) - float(features["home_distance_traveled"])) / 525.0)
        + ((float(features["home_injury_impact"]) - float(features["away_injury_impact"])) * 10.0)
        + (float(features["ref_home_bias"]) * 6.0)
        + (float(features["ref_foul_bias"]) * 1.5)
    )


def _fallback_total(features: Mapping[str, float]) -> float:
    """Heuristic projected total when the totals regressor is unavailable."""
    avg_pace = (float(features["home_pace_l10"]) + float(features["away_pace_l10"])) / 2.0
    injury_drag = abs(float(features["home_injury_impact"])) + abs(float(features["away_injury_impact"]))
    total = (
        116.0
        + (avg_pace * 1.08)
        + (float(features["ref_total_bias"]) * 18.0)
        + (float(features["ref_foul_bias"]) * 7.0)
        - (injury_drag * 10.0)
        - ((float(features["home_b2b"]) + float(features["away_b2b"])) * 1.5)
    )
    return _clamp(total, 180.0, 265.0)


def _rank_feature_scores(
    scores: Mapping[str, float],
    features: Mapping[str, float],
    top_n: int,
) -> List[Dict[str, Any]]:
    """Convert raw feature scores into normalized driver records."""
    ranked = sorted(
        ((feature_name, abs(float(score))) for feature_name, score in scores.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    ranked = [(feature_name, score) for feature_name, score in ranked if score > 0][:top_n]
    total_score = sum(score for _, score in ranked) or 1.0
    return [
        {
            "feature": feature_name,
            "importance": round(score / total_score, 4),
            "game_impact": round(score / total_score, 4),
            "value": round(float(features.get(feature_name, 0.0)), 4),
        }
        for feature_name, score in ranked
    ]


def _fallback_top_features(features: Mapping[str, float], top_n: int) -> List[Dict[str, Any]]:
    """Return heuristic feature drivers when trained model importances are unavailable."""
    return _rank_feature_scores(_fallback_feature_contributions(features), features, top_n)


def _model_top_features(
    model,
    features: Mapping[str, float],
    top_n: int,
) -> List[Dict[str, Any]]:
    """Approximate the most important features for the current game."""
    if model is None:
        return _fallback_top_features(features, top_n)

    scaler = model.named_steps.get("scaler")
    estimator = model.named_steps.get("xgb")
    if estimator is None:
        return _fallback_top_features(features, top_n)

    importances = getattr(estimator, "feature_importances_", None)
    if importances is None or len(importances) != len(CONSOLIDATED_FEATURES):
        return _fallback_top_features(features, top_n)

    row = np.array([build_feature_row(features)], dtype=float)
    transformed = scaler.transform(row)[0] if scaler is not None else row[0]
    raw_scores = {
        feature_name: abs(float(transformed[index])) * float(importances[index])
        for index, feature_name in enumerate(CONSOLIDATED_FEATURES)
    }
    top_features = _rank_feature_scores(raw_scores, features, top_n)
    if not top_features:
        return _fallback_top_features(features, top_n)

    normalized_importance_total = float(np.sum(importances)) or 1.0
    for entry in top_features:
        feature_index = CONSOLIDATED_FEATURES.index(entry["feature"])
        entry["importance"] = round(float(importances[feature_index]) / normalized_importance_total, 4)
    return top_features


def predict(
    features: Mapping[str, Any],
    top_n: int = DEFAULT_TOP_FEATURES,
) -> Dict[str, Any]:
    """Load consolidated models, score one game, and return projections plus drivers."""
    ensure_model_dir()
    normalized_features = _feature_map(features)
    row = np.array([build_feature_row(normalized_features)], dtype=float)

    win_model = _load_model("win_prob")
    spread_model = _load_model("spread")
    total_model = _load_model("total")

    model_source = {
        "win_prob": "trained" if win_model is not None else "heuristic",
        "spread": "trained" if spread_model is not None else "heuristic",
        "total": "trained" if total_model is not None else "heuristic",
    }

    if win_model is not None:
        home_win_prob = float(win_model.predict_proba(row)[0][1])
    else:
        home_win_prob = _fallback_home_win_prob(normalized_features)

    if spread_model is not None:
        projected_margin = float(spread_model.predict(row)[0])
    else:
        projected_margin = _fallback_margin(normalized_features)

    if total_model is not None:
        projected_total = float(total_model.predict(row)[0])
    else:
        projected_total = _fallback_total(normalized_features)

    return {
        "home_win_prob": round(_clamp(home_win_prob, 0.01, 0.99), 4),
        "projected_spread": round(-projected_margin, 2),
        "projected_total": round(_clamp(projected_total, 180.0, 265.0), 2),
        "top_features": _model_top_features(win_model, normalized_features, top_n=top_n),
        "model_source": model_source,
    }
