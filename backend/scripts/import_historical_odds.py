"""Import historical NBA odds CSV data into the historical_odds table."""
import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd
from nba_api.stats.static import teams as nba_teams

from bootstrap import configure_paths

configure_paths()

from market.db import get_db  # noqa: E402
from season import compute_current_season  # noqa: E402

TEAM_ALIASES = {
    "LOS ANGELES CLIPPERS": "LAC",
    "LA CLIPPERS": "LAC",
    "LOS ANGELES LAKERS": "LAL",
    "LA LAKERS": "LAL",
    "BROOKLYN": "BKN",
    "PHOENIX": "PHX",
    "SAN ANTONIO": "SAS",
    "NEW ORLEANS": "NOP",
    "UTAH": "UTA",
}
for team in nba_teams.get_teams():
    TEAM_ALIASES[team["abbreviation"].upper()] = team["abbreviation"].upper()
    TEAM_ALIASES[team["full_name"].upper()] = team["abbreviation"].upper()
    TEAM_ALIASES[team["nickname"].upper()] = team["abbreviation"].upper()
    TEAM_ALIASES[team["city"].upper()] = team["abbreviation"].upper()

FIELD_ALIASES = {
    "season": ("season", "year", "league_season"),
    "game_id": ("game_id", "event_id", "match_id"),
    "game_date": ("game_date", "date", "commence_date", "start_date"),
    "home_team": ("home_team", "home", "home_abbr", "home_team_abbr", "team_home"),
    "away_team": ("away_team", "away", "away_abbr", "away_team_abbr", "team_away"),
    "bookmaker": ("bookmaker", "sportsbook", "book"),
    "home_open_price": ("home_open_price", "ml_home_open", "home_moneyline_open", "home_price_open"),
    "away_open_price": ("away_open_price", "ml_away_open", "away_moneyline_open", "away_price_open"),
    "home_close_price": ("home_close_price", "ml_home_close", "home_moneyline_close", "home_price_close", "home_odds"),
    "away_close_price": ("away_close_price", "ml_away_close", "away_moneyline_close", "away_price_close", "away_odds"),
    "home_open_spread": ("home_open_spread", "spread_home_open", "home_spread_open"),
    "away_open_spread": ("away_open_spread", "spread_away_open", "away_spread_open"),
    "home_close_spread": ("home_close_spread", "spread_home_close", "home_spread_close", "home_spread"),
    "away_close_spread": ("away_close_spread", "spread_away_close", "away_spread_close", "away_spread"),
    "total_open": ("total_open", "ou_open", "open_total"),
    "total_close": ("total_close", "ou_close", "closing_total", "total"),
}


def _normalize_header(value: str) -> str:
    """Normalize a CSV header for alias matching."""
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("%", "pct")
        .replace("-", "_")
        .replace(" ", "_")
    )


def _coerce_float(value: object) -> Optional[float]:
    """Convert a CSV cell into a float when possible."""
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _normalize_team(value: object) -> Optional[str]:
    """Normalize team names into NBA abbreviations."""
    if value in (None, ""):
        return None
    cleaned = str(value).strip().upper()
    return TEAM_ALIASES.get(cleaned, cleaned if len(cleaned) == 3 else None)


def _derive_season(game_date: str) -> str:
    """Infer season text from a YYYY-MM-DD date."""
    parsed = pd.to_datetime(game_date)
    year = int(parsed.year)
    month = int(parsed.month)
    start_year = year if month >= 10 else year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _extract_value(row: Dict[str, object], field_name: str) -> object:
    """Read the first matching alias from a normalized row."""
    for alias in FIELD_ALIASES[field_name]:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
    return None


def _normalized_rows(path: Path, delimiter: str) -> Iterable[Dict[str, object]]:
    """Yield normalized CSV rows."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for raw_row in reader:
            yield {_normalize_header(key): value for key, value in raw_row.items()}


def import_file(path: Path, bookmaker_override: Optional[str] = None, delimiter: str = ",") -> Dict[str, int]:
    """Import one historical odds CSV into SQLite."""
    conn = get_db()
    inserted = 0
    skipped = 0
    try:
        for row in _normalized_rows(path, delimiter=delimiter):
            game_date_raw = _extract_value(row, "game_date")
            home_team_raw = _extract_value(row, "home_team")
            away_team_raw = _extract_value(row, "away_team")
            if not game_date_raw or not home_team_raw or not away_team_raw:
                skipped += 1
                continue

            game_date = pd.to_datetime(game_date_raw).strftime("%Y-%m-%d")
            home_team = _normalize_team(home_team_raw)
            away_team = _normalize_team(away_team_raw)
            if not home_team or not away_team:
                skipped += 1
                continue

            season = _extract_value(row, "season")
            season = str(season).strip() if season not in (None, "") else _derive_season(game_date)
            bookmaker = bookmaker_override or _extract_value(row, "bookmaker") or "historical_import"

            home_close_price = _coerce_float(_extract_value(row, "home_close_price"))
            away_close_price = _coerce_float(_extract_value(row, "away_close_price"))
            if home_close_price is None or away_close_price is None:
                skipped += 1
                continue

            conn.execute(
                """
                INSERT INTO historical_odds (
                    season, game_id, game_date, home_team, away_team, bookmaker,
                    home_open_price, away_open_price, home_close_price, away_close_price,
                    home_open_spread, away_open_spread, home_close_spread, away_close_spread,
                    total_open, total_close, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_date, home_team, away_team, bookmaker) DO UPDATE SET
                    season = excluded.season,
                    game_id = excluded.game_id,
                    home_open_price = excluded.home_open_price,
                    away_open_price = excluded.away_open_price,
                    home_close_price = excluded.home_close_price,
                    away_close_price = excluded.away_close_price,
                    home_open_spread = excluded.home_open_spread,
                    away_open_spread = excluded.away_open_spread,
                    home_close_spread = excluded.home_close_spread,
                    away_close_spread = excluded.away_close_spread,
                    total_open = excluded.total_open,
                    total_close = excluded.total_close,
                    source_file = excluded.source_file,
                    imported_at = CURRENT_TIMESTAMP
                """,
                (
                    season,
                    _extract_value(row, "game_id"),
                    game_date,
                    home_team,
                    away_team,
                    str(bookmaker),
                    _coerce_float(_extract_value(row, "home_open_price")),
                    _coerce_float(_extract_value(row, "away_open_price")),
                    home_close_price,
                    away_close_price,
                    _coerce_float(_extract_value(row, "home_open_spread")),
                    _coerce_float(_extract_value(row, "away_open_spread")),
                    _coerce_float(_extract_value(row, "home_close_spread")),
                    _coerce_float(_extract_value(row, "away_close_spread")),
                    _coerce_float(_extract_value(row, "total_open")),
                    _coerce_float(_extract_value(row, "total_close")),
                    path.name,
                ),
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()

    return {"inserted": inserted, "skipped": skipped}


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Import historical NBA odds CSV data.")
    parser.add_argument("csv_path", type=Path, help="Path to the historical odds CSV file.")
    parser.add_argument("--bookmaker", help="Override bookmaker/source name.")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter, default ','.")
    args = parser.parse_args(argv)

    if not args.csv_path.exists():
        print(f"CSV file not found: {args.csv_path}", file=sys.stderr)
        return 1

    result = import_file(args.csv_path, bookmaker_override=args.bookmaker, delimiter=args.delimiter)
    current_season = compute_current_season()
    print(
        f"Imported historical odds from {args.csv_path.name}: "
        f"{result['inserted']} rows upserted, {result['skipped']} skipped. "
        f"Current season context: {current_season}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
