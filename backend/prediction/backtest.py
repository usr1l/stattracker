"""Backtesting engine for evaluating prediction accuracy, ROI, CLV, and calibration."""
from typing import Any, Dict, List, Optional, Tuple

from market.db import get_db
from prediction.predict import predict_game
from season import load_seasons

KELLY_FRACTION_CANDIDATES = (0.10, 0.25, 0.50, 0.75, 1.00)
CONFIDENCE_BUCKET_RANGES: Tuple[Tuple[float, float], ...] = (
    (0.50, 0.55),
    (0.55, 0.60),
    (0.60, 0.65),
    (0.65, 0.70),
    (0.70, 1.01),
)
EDGE_TIER_RANGES: Tuple[Tuple[str, float, Optional[float]], ...] = (
    ("<2%", 0.0, 0.02),
    ("2-5%", 0.02, 0.05),
    ("5%+", 0.05, None),
)


def decimal_odds_to_prob(decimal_odds: float) -> float:
    """Convert decimal odds into implied probability."""
    if decimal_odds <= 0:
        return 0.0
    return 1.0 / decimal_odds


def _extract_model_home_prob(game: Dict[str, Any]) -> float:
    """Read a model probability from either the old or new prediction format."""
    if "model_home_prob" in game:
        return float(game["model_home_prob"])

    projections = game.get("projections")
    if isinstance(projections, dict):
        if "home_win_prob" in projections:
            return float(projections["home_win_prob"])
        final = projections.get("final")
        if isinstance(final, dict) and "home_win_prob" in final:
            return float(final["home_win_prob"])

    if "home_win_prob" in game:
        return float(game["home_win_prob"])

    raise KeyError(
        "Game is missing model probability; expected model_home_prob or projections.home_win_prob"
    )


def calculate_kelly_criterion(prob: float, decimal_odds: float, fraction: float = 0.25) -> float:
    """
    f = (bp - q) / b
    b = decimal_odds - 1 (net odds)
    p = prob of winning
    q = 1 - p (prob of losing)
    """
    if prob <= 0 or prob >= 1 or decimal_odds <= 1.0:
        return 0.0

    b = decimal_odds - 1.0
    p = prob
    q = 1.0 - p
    kelly_f = (b * p - q) / b
    if kelly_f <= 0:
        return 0.0
    return kelly_f * fraction


def _bucket_label(lower: float, upper: float) -> str:
    """Format a confidence bucket label."""
    if upper >= 1.0:
        return f"{int(lower * 100)}%+"
    return f"{int(lower * 100)}-{int(upper * 100)}%"


def _get_confidence_bucket(confidence: float) -> str:
    """Map a confidence value into a probability bucket."""
    for lower, upper in CONFIDENCE_BUCKET_RANGES:
        if lower <= confidence < upper:
            return _bucket_label(lower, upper)
    return _bucket_label(*CONFIDENCE_BUCKET_RANGES[-1])


def _get_edge_tier(edge: float) -> str:
    """Map an edge into a confidence tier."""
    for label, lower, upper in EDGE_TIER_RANGES:
        if edge >= lower and (upper is None or edge < upper):
            return label
    return EDGE_TIER_RANGES[0][0]


def _build_bucket_state() -> Dict[str, Dict[str, float]]:
    """Create mutable bucket accumulators."""
    return {
        _bucket_label(lower, upper): {
            "bets": 0.0,
            "wins": 0.0,
            "edge_sum": 0.0,
            "stake": 0.0,
            "profit": 0.0,
            "prob_sum": 0.0,
            "clv_sum": 0.0,
            "pushes": 0.0,
        }
        for lower, upper in CONFIDENCE_BUCKET_RANGES
    }


def _build_edge_tier_state() -> Dict[str, Dict[str, float]]:
    """Create mutable edge-tier accumulators."""
    return {
        label: {
            "bets": 0.0,
            "wins": 0.0,
            "edge_sum": 0.0,
            "stake": 0.0,
            "profit": 0.0,
            "clv_sum": 0.0,
            "pushes": 0.0,
        }
        for label, _, _ in EDGE_TIER_RANGES
    }


def _settle_moneyline_bet(
    selected_side: str,
    selected_entry_price: float,
    home_score: float,
    away_score: float,
    bet_size: float,
) -> Dict[str, float]:
    """Settle one moneyline wager and return the bankroll impact."""
    if float(home_score) == float(away_score):
        return {
            "result": "push",
            "bankroll_delta": 0.0,
            "profit": 0.0,
        }

    home_won = float(home_score) > float(away_score)
    selected_won = (selected_side == "home" and home_won) or (selected_side == "away" and not home_won)
    if selected_won:
        return {
            "result": "win",
            "bankroll_delta": bet_size * (float(selected_entry_price) - 1.0),
            "profit": bet_size * (float(selected_entry_price) - 1.0),
        }

    return {
        "result": "loss",
        "bankroll_delta": -bet_size,
        "profit": -bet_size,
    }


def _risk_adjusted_score(result: Dict[str, Any], starting_bankroll: float) -> float:
    """Prefer higher ROI, but penalize large drawdowns when picking a Kelly fraction."""
    if starting_bankroll <= 0:
        return float(result.get("roi_percent", 0.0))
    drawdown_pct = (float(result.get("max_drawdown", 0.0)) / float(starting_bankroll)) * 100.0
    return float(result.get("roi_percent", 0.0)) - (drawdown_pct * 0.45)


def _coalesce_float(*values: Any) -> Optional[float]:
    """Return the first non-empty numeric value."""
    for value in values:
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _entry_price(game: Dict[str, Any], side: str) -> Optional[float]:
    """Read the simulated entry price for one side."""
    if side == "home":
        return _coalesce_float(game.get("home_open_price"), game.get("home_odds"))
    return _coalesce_float(game.get("away_open_price"), game.get("away_odds"))


def _closing_price(game: Dict[str, Any], side: str) -> Optional[float]:
    """Read the closing price for one side."""
    if side == "home":
        return _coalesce_float(game.get("home_close_price"), game.get("home_odds"))
    return _coalesce_float(game.get("away_close_price"), game.get("away_odds"))


def _entry_spread(game: Dict[str, Any], side: str) -> Optional[float]:
    """Read the simulated entry spread for one side."""
    if side == "home":
        return _coalesce_float(game.get("home_open_spread"))
    away_spread = _coalesce_float(game.get("away_open_spread"))
    if away_spread is not None:
        return away_spread
    home_spread = _coalesce_float(game.get("home_open_spread"))
    return -home_spread if home_spread is not None else None


def _closing_spread(game: Dict[str, Any], side: str) -> Optional[float]:
    """Read the closing spread for one side."""
    if side == "home":
        return _coalesce_float(game.get("home_close_spread"))
    away_spread = _coalesce_float(game.get("away_close_spread"))
    if away_spread is not None:
        return away_spread
    home_spread = _coalesce_float(game.get("home_close_spread"))
    return -home_spread if home_spread is not None else None


def _compute_clv(game: Dict[str, Any], side: str) -> Dict[str, Optional[float]]:
    """Compute price-based and spread-based closing line value for one bet."""
    entry_price = _entry_price(game, side)
    close_price = _closing_price(game, side)
    clv_price = None
    if entry_price and close_price and entry_price > 1.0 and close_price > 1.0:
        clv_price = decimal_odds_to_prob(close_price) - decimal_odds_to_prob(entry_price)

    entry_spread = _entry_spread(game, side)
    close_spread = _closing_spread(game, side)
    clv_spread = None
    if entry_spread is not None and close_spread is not None:
        if side == "home":
            clv_spread = float(entry_spread) - float(close_spread)
        else:
            clv_spread = float(close_spread) - float(entry_spread)

    return {
        "clv_price": clv_price,
        "clv_spread": clv_spread,
    }


def _average(values: List[float]) -> float:
    """Return the arithmetic mean, or zero."""
    return (sum(values) / len(values)) if values else 0.0


def _load_completed_games(
    seasons: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Load completed home/away game results from team_game_logs."""
    _, default_seasons = load_seasons()
    selected_seasons = seasons or default_seasons[:3]

    conn = get_db()
    try:
        conditions = ["pts IS NOT NULL"]
        params: List[Any] = []
        if selected_seasons:
            placeholders = ",".join("?" for _ in selected_seasons)
            conditions.append(f"season IN ({placeholders})")
            params.extend(selected_seasons)
        if date_from:
            conditions.append("game_date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("game_date <= ?")
            params.append(date_to)

        rows = conn.execute(
            f"""
            SELECT season, game_id, game_date, team_abbr, matchup, pts
            FROM team_game_logs
            WHERE {' AND '.join(conditions)}
            ORDER BY game_date ASC, game_id ASC
            """
            + (" LIMIT ?" if limit else ""),
            tuple(params + ([int(limit)] if limit else [])),
        ).fetchall()
    finally:
        conn.close()

    by_game: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_game.setdefault(str(row["game_id"]), []).append(dict(row))

    games: List[Dict[str, Any]] = []
    for game_id, team_rows in by_game.items():
        if len(team_rows) < 2:
            continue
        home_row = next((r for r in team_rows if "vs." in (r.get("matchup") or "")), None)
        away_row = next((r for r in team_rows if "@" in (r.get("matchup") or "")), None)
        if home_row is None or away_row is None:
            home_row, away_row = team_rows[0], team_rows[1]

        try:
            home_score = float(home_row["pts"])
            away_score = float(away_row["pts"])
        except (TypeError, ValueError):
            continue

        games.append(
            {
                "season": home_row["season"],
                "game_id": game_id,
                "game_date": home_row["game_date"],
                "date": home_row["game_date"],
                "home_team": home_row["team_abbr"],
                "away_team": away_row["team_abbr"],
                "home_score": home_score,
                "away_score": away_score,
            }
        )
    return games


def _load_historical_odds(
    seasons: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    """Load historical odds rows keyed by date and matchup."""
    _, default_seasons = load_seasons()
    selected_seasons = seasons or default_seasons[:3]

    conn = get_db()
    try:
        conditions = ["1 = 1"]
        params: List[Any] = []
        if selected_seasons:
            placeholders = ",".join("?" for _ in selected_seasons)
            conditions.append(f"(season IN ({placeholders}) OR season IS NULL)")
            params.extend(selected_seasons)
        if date_from:
            conditions.append("game_date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("game_date <= ?")
            params.append(date_to)

        rows = conn.execute(
            f"""
            SELECT *
            FROM historical_odds
            WHERE {' AND '.join(conditions)}
            ORDER BY imported_at DESC, id DESC
            """,
            tuple(params),
        ).fetchall()
    finally:
        conn.close()

    odds_by_matchup: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        payload = dict(row)
        key = (
            str(payload["game_date"]),
            str(payload["home_team"]).upper(),
            str(payload["away_team"]).upper(),
        )
        if key not in odds_by_matchup:
            odds_by_matchup[key] = payload
    return odds_by_matchup


def load_historical_backtest_games(
    seasons: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = None,
    attach_model_predictions: bool = True,
) -> List[Dict[str, Any]]:
    """Join historical game results with imported odds for DB-backed backtests."""
    completed_games = _load_completed_games(
        seasons=seasons,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    odds_by_matchup = _load_historical_odds(
        seasons=seasons,
        date_from=date_from,
        date_to=date_to,
    )

    backtest_games: List[Dict[str, Any]] = []
    for game in completed_games:
        key = (game["game_date"], game["home_team"], game["away_team"])
        odds_row = odds_by_matchup.get(key)
        if odds_row is None:
            continue

        payload = {
            **game,
            "bookmaker": odds_row.get("bookmaker"),
            "home_open_price": odds_row.get("home_open_price"),
            "away_open_price": odds_row.get("away_open_price"),
            "home_close_price": odds_row.get("home_close_price"),
            "away_close_price": odds_row.get("away_close_price"),
            "home_open_spread": odds_row.get("home_open_spread"),
            "away_open_spread": odds_row.get("away_open_spread"),
            "home_close_spread": odds_row.get("home_close_spread"),
            "away_close_spread": odds_row.get("away_close_spread"),
            "total_open": odds_row.get("total_open"),
            "total_close": odds_row.get("total_close"),
            # Legacy compatibility keys used by the simulator.
            "home_odds": odds_row.get("home_close_price"),
            "away_odds": odds_row.get("away_close_price"),
        }

        if attach_model_predictions:
            try:
                prediction = predict_game(
                    payload["home_team"],
                    payload["away_team"],
                    payload["game_date"],
                    game_id=payload.get("game_id"),
                )
                payload["projections"] = prediction.get("projections", {})
                payload["key_drivers"] = prediction.get("key_drivers", [])
                payload["model_home_prob"] = float(payload["projections"]["home_win_prob"])
            except Exception:
                continue

        backtest_games.append(payload)

    if limit:
        return backtest_games[: int(limit)]
    return backtest_games


def _simulate_backtest(
    games: List[Dict[str, Any]],
    starting_bankroll: float,
    kelly_fraction: float,
    include_history: bool = True,
) -> Dict[str, Any]:
    """Run one backtest simulation for a specific Kelly fraction."""
    bankroll = starting_bankroll
    wins = 0
    losses = 0
    pushes = 0
    total_bets = 0
    brier_sum = 0.0
    bankroll_history = (
        [{"index": 0, "label": "Start", "bankroll": bankroll}] if include_history else []
    )

    max_drawdown = 0.0
    peak_bankroll = bankroll
    total_edge = 0.0
    total_bet_size = 0.0
    confidence_bucket_state = _build_bucket_state()
    edge_tier_state = _build_edge_tier_state()
    clv_price_values: List[float] = []
    clv_spread_values: List[float] = []
    bet_history: List[Dict[str, Any]] = []

    for index, game in enumerate(games, start=1):
        home_score = float(game["home_score"])
        away_score = float(game["away_score"])
        home_won = home_score > away_score
        if home_score == away_score:
            actual_result = 0.5
        else:
            actual_result = 1.0 if home_won else 0.0
        model_prob = _extract_model_home_prob(game)
        brier_sum += (model_prob - actual_result) ** 2

        home_entry_price = _entry_price(game, "home")
        away_entry_price = _entry_price(game, "away")
        if home_entry_price is None or away_entry_price is None:
            continue

        home_implied = decimal_odds_to_prob(home_entry_price)
        away_implied = decimal_odds_to_prob(away_entry_price)

        selected_side = None
        selected_prob = None
        selected_entry_price = None
        selected_implied = None
        bet_size = 0.0
        profit = 0.0

        if model_prob > home_implied:
            selected_side = "home"
            selected_prob = model_prob
            selected_entry_price = home_entry_price
            selected_implied = home_implied
        elif (1.0 - model_prob) > away_implied:
            selected_side = "away"
            selected_prob = 1.0 - model_prob
            selected_entry_price = away_entry_price
            selected_implied = away_implied

        if selected_side and selected_prob is not None and selected_entry_price is not None and selected_implied is not None:
            edge = max(0.0, float(selected_prob) - float(selected_implied))
            bet_size = calculate_kelly_criterion(
                float(selected_prob),
                float(selected_entry_price),
                fraction=kelly_fraction,
            ) * bankroll
        else:
            edge = 0.0

        if bet_size > 0 and selected_side is not None and selected_prob is not None:
            total_bets += 1
            total_bet_size += bet_size
            total_edge += edge
            settlement = _settle_moneyline_bet(
                selected_side=selected_side,
                selected_entry_price=float(selected_entry_price),
                home_score=home_score,
                away_score=away_score,
                bet_size=bet_size,
            )
            profit = float(settlement["profit"])
            bankroll += float(settlement["bankroll_delta"])
            if settlement["result"] == "win":
                wins += 1
            elif settlement["result"] == "loss":
                losses += 1
            else:
                pushes += 1

            clv = _compute_clv(game, selected_side)
            if clv["clv_price"] is not None:
                clv_price_values.append(float(clv["clv_price"]))
            if clv["clv_spread"] is not None:
                clv_spread_values.append(float(clv["clv_spread"]))

            confidence_label = _get_confidence_bucket(float(selected_prob))
            confidence_bucket = confidence_bucket_state[confidence_label]
            confidence_bucket["bets"] += 1
            confidence_bucket["wins"] += 1 if settlement["result"] == "win" else 0
            confidence_bucket["pushes"] += 1 if settlement["result"] == "push" else 0
            confidence_bucket["edge_sum"] += edge
            confidence_bucket["stake"] += bet_size
            confidence_bucket["profit"] += profit
            confidence_bucket["prob_sum"] += float(selected_prob)
            confidence_bucket["clv_sum"] += float(clv["clv_price"] or 0.0)

            edge_tier_label = _get_edge_tier(edge)
            edge_tier = edge_tier_state[edge_tier_label]
            edge_tier["bets"] += 1
            edge_tier["wins"] += 1 if settlement["result"] == "win" else 0
            edge_tier["pushes"] += 1 if settlement["result"] == "push" else 0
            edge_tier["edge_sum"] += edge
            edge_tier["stake"] += bet_size
            edge_tier["profit"] += profit
            edge_tier["clv_sum"] += float(
                clv["clv_spread"] if clv["clv_spread"] is not None else (clv["clv_price"] or 0.0)
            )

            if include_history:
                bet_history.append(
                    {
                        "index": index,
                        "date": game.get("date") or game.get("game_date"),
                        "matchup": f"{game.get('away_team')} @ {game.get('home_team')}",
                        "side": selected_side,
                        "result": settlement["result"],
                        "edge_pct": round(edge * 100.0, 3),
                        "return_pct": round((profit / bet_size) * 100.0, 3),
                        "bet_size": round(bet_size, 2),
                        "profit": round(profit, 2),
                        "clv_price": round(float(clv["clv_price"]), 4) if clv["clv_price"] is not None else None,
                        "clv_spread": round(float(clv["clv_spread"]), 3) if clv["clv_spread"] is not None else None,
                    }
                )

        if bankroll > peak_bankroll:
            peak_bankroll = bankroll
        drawdown = peak_bankroll - bankroll
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        if include_history:
            bankroll_history.append(
                {
                    "index": index,
                    "label": game.get("date") or game.get("game_date") or f"Game {index}",
                    "bankroll": bankroll,
                    "bet_placed": bet_size > 0,
                }
            )

    brier = brier_sum / len(games) if games else 0.0
    roi = ((bankroll - starting_bankroll) / starting_bankroll) * 100.0 if starting_bankroll else 0.0

    confidence_buckets = []
    for lower, upper in CONFIDENCE_BUCKET_RANGES:
        label = _bucket_label(lower, upper)
        bucket = confidence_bucket_state[label]
        bets = int(bucket["bets"])
        pushes_in_bucket = int(bucket["pushes"])
        decisions = max(0, bets - pushes_in_bucket)
        avg_prob = float(bucket["prob_sum"]) / bets if bets else 0.0
        win_rate = float(bucket["wins"]) / decisions if decisions else 0.0
        confidence_buckets.append(
            {
                "label": label,
                "bets": bets,
                "pushes": pushes_in_bucket,
                "win_rate": win_rate,
                "average_model_prob": avg_prob,
                "average_edge": (float(bucket["edge_sum"]) / bets) if bets else 0.0,
                "roi_percent": ((float(bucket["profit"]) / float(bucket["stake"])) * 100.0) if bucket["stake"] else 0.0,
                "calibration_gap": win_rate - avg_prob,
                "average_clv": (float(bucket["clv_sum"]) / bets) if bets else 0.0,
            }
        )

    confidence_tiers = []
    for label, _, _ in EDGE_TIER_RANGES:
        tier = edge_tier_state[label]
        bets = int(tier["bets"])
        pushes_in_tier = int(tier["pushes"])
        decisions = max(0, bets - pushes_in_tier)
        win_rate = float(tier["wins"]) / decisions if decisions else 0.0
        confidence_tiers.append(
            {
                "label": label,
                "bets": bets,
                "pushes": pushes_in_tier,
                "win_rate": win_rate,
                "average_edge": (float(tier["edge_sum"]) / bets) if bets else 0.0,
                "roi_percent": ((float(tier["profit"]) / float(tier["stake"])) * 100.0) if tier["stake"] else 0.0,
                "average_clv": (float(tier["clv_sum"]) / bets) if bets else 0.0,
            }
        )

    average_clv_spread = _average(clv_spread_values)
    average_clv_implied_prob = _average(clv_price_values)
    average_clv = average_clv_spread if clv_spread_values else average_clv_implied_prob
    clv_unit = "points" if clv_spread_values else "implied_prob"

    return {
        "games_processed": len(games),
        "total_bets": total_bets,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": (wins / (wins + losses)) if (wins + losses) > 0 else 0.0,
        "starting_bankroll": starting_bankroll,
        "ending_bankroll": bankroll,
        "roi_percent": roi,
        "max_drawdown": max_drawdown,
        "brier_score": brier,
        "bankroll_history": bankroll_history,
        "bet_history": bet_history,
        "average_edge": (total_edge / total_bets) if total_bets > 0 else 0.0,
        "average_bet_size": (total_bet_size / total_bets) if total_bets > 0 else 0.0,
        "average_clv": average_clv,
        "average_clv_spread": average_clv_spread,
        "average_clv_implied_prob": average_clv_implied_prob,
        "clv_unit": clv_unit,
        "confidence_buckets": confidence_buckets,
        "confidence_tiers": confidence_tiers,
    }


def _build_fraction_sweep(
    games: List[Dict[str, Any]],
    starting_bankroll: float,
) -> List[Dict[str, Any]]:
    """Compare common Kelly fractions on the same game set."""
    sweep = []
    for fraction in KELLY_FRACTION_CANDIDATES:
        result = _simulate_backtest(
            games=games,
            starting_bankroll=starting_bankroll,
            kelly_fraction=fraction,
            include_history=False,
        )
        sweep.append(
            {
                "kelly_fraction": fraction,
                "ending_bankroll": result["ending_bankroll"],
                "roi_percent": result["roi_percent"],
                "max_drawdown": result["max_drawdown"],
                "total_bets": result["total_bets"],
                "win_rate": result["win_rate"],
                "average_clv": result["average_clv"],
                "score": _risk_adjusted_score(result, starting_bankroll),
            }
        )
    return sweep


def run_backtest(
    games: Optional[List[Dict[str, Any]]] = None,
    starting_bankroll: float = 10000.0,
    kelly_fraction: float = 0.25,
    seasons: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run a backtest from either supplied games or DB-backed historical odds/results.
    Expected manual game format:
    {
      "date": "...",
      "home_team": "...", "away_team": "...",
      "home_score": 110, "away_score": 105,
      "home_odds": 1.5, "away_odds": 2.6,
      "model_home_prob": 0.70
    }
    """
    if starting_bankroll <= 0:
        raise ValueError("starting_bankroll must be positive")
    if kelly_fraction <= 0 or kelly_fraction > 1:
        raise ValueError("kelly_fraction must be between 0 and 1")

    resolved_games = games or load_historical_backtest_games(
        seasons=seasons,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        attach_model_predictions=True,
    )
    if not resolved_games:
        raise ValueError("No historical games were available for backtesting")

    result = _simulate_backtest(
        games=resolved_games,
        starting_bankroll=starting_bankroll,
        kelly_fraction=kelly_fraction,
        include_history=True,
    )
    fraction_sweep = _build_fraction_sweep(resolved_games, starting_bankroll)
    recommended_fraction = kelly_fraction
    if fraction_sweep:
        recommended_fraction = max(
            fraction_sweep,
            key=lambda candidate: (candidate["score"], candidate["ending_bankroll"]),
        )["kelly_fraction"]

    result["kelly_fraction"] = kelly_fraction
    result["recommended_kelly_fraction"] = recommended_fraction
    result["fraction_sweep"] = fraction_sweep
    result["data_source"] = "manual_payload" if games else "historical_odds_db"
    return result
