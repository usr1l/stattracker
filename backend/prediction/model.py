"""Phase 1 ML Model: Logistic Regression for ML, Linear for Spreads/Totals."""
import os
import joblib
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV

MODEL_DIR = Path(__file__).resolve().parent.parent / "instance" / "models"
WIN_PROB_MODEL_FILE = MODEL_DIR / "win_prob.pkl"
SPREAD_MODEL_FILE = MODEL_DIR / "spread.pkl"
TOTAL_MODEL_FILE = MODEL_DIR / "total.pkl"

# Expected features from build_game_features()
FEATURE_NAMES = [
    "elo_diff", "home_net_rating_l10", "away_net_rating_l10", 
    "net_rating_diff", "home_rest_days", "away_rest_days", 
    "home_b2b", "away_b2b"
]

def ensure_model_dir():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

def train_baseline_models(X: np.ndarray, y_win: np.ndarray, y_spread: np.ndarray, y_total: np.ndarray) -> None:
    """Train and save the baseline models."""
    ensure_model_dir()
    
    # 1. Win Probability: Logistic Regression calibrated
    clf = Pipeline([
        ('scaler', StandardScaler()),
        ('lr', LogisticRegression(C=1.0, solver='lbfgs'))
    ])
    
    calibrated_clf = CalibratedClassifierCV(estimator=clf, method='sigmoid', cv=5)
    calibrated_clf.fit(X, y_win)
    joblib.dump(calibrated_clf, WIN_PROB_MODEL_FILE)
    
    # 2. Spread (Margin): Linear Regression
    # y_spread is (Home Score - Away Score)
    spread_reg = Pipeline([
        ('scaler', StandardScaler()),
        ('lr', LinearRegression())
    ])
    spread_reg.fit(X, y_spread)
    joblib.dump(spread_reg, SPREAD_MODEL_FILE)
    
    # 3. Total Points: Linear Regression
    # y_total is (Home Score + Away Score)
    total_reg = Pipeline([
        ('scaler', StandardScaler()),
        ('lr', LinearRegression())
    ])
    total_reg.fit(X, y_total)
    joblib.dump(total_reg, TOTAL_MODEL_FILE)


def predict(features: Dict[str, Any]) -> Dict[str, float]:
    """
    Given a game feature dict, load models and return predictions.
    If models aren't trained yet, returns dummy fallback values to ensure API works.
    """
    ensure_model_dir()
    
    x = np.array([[features[f] for f in FEATURE_NAMES]])
    
    res = {}
    
    if WIN_PROB_MODEL_FILE.exists():
        clf = joblib.load(WIN_PROB_MODEL_FILE)
        # Assuming class 1 is home win
        res["home_win_prob"] = float(clf.predict_proba(x)[0][1])
    else:
        # Fallback to pure ELO expected win
        from prediction.elo import get_expected_win_prob
        res["home_win_prob"] = float(get_expected_win_prob(features["elo_diff"]))
        
    if SPREAD_MODEL_FILE.exists():
        reg = joblib.load(SPREAD_MODEL_FILE)
        # Margin (home score - away score)
        margin = float(reg.predict(x)[0])
        res["projected_margin"] = margin
        res["projected_spread"] = -margin  # Spread convention: favored by 5 = -5
    else:
        # 1 ELO point ~= 0.033 points of margin roughly
        margin = features["elo_diff"] / 30.0
        res["projected_margin"] = margin
        res["projected_spread"] = -margin
        
    if TOTAL_MODEL_FILE.exists():
        treg = joblib.load(TOTAL_MODEL_FILE)
        res["projected_total"] = float(treg.predict(x)[0])
    else:
        # NBA average ~225
        res["projected_total"] = 225.0
        
    return res
