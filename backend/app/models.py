"""ORM models mirrored from the legacy SQLite schema."""
from sqlalchemy.sql import func

from app.extensions import db


class OddsHistory(db.Model):
    __tablename__ = "odds_history"
    __table_args__ = (db.Index("idx_odds_game_id", "game_id"),)

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String, nullable=False)
    home_team = db.Column(db.String, nullable=False)
    away_team = db.Column(db.String, nullable=False)
    commence_time = db.Column(db.String, nullable=False)
    bookmaker = db.Column(db.String, nullable=False)
    market_type = db.Column(db.String, nullable=False)
    home_price = db.Column(db.Float)
    away_price = db.Column(db.Float)
    home_point = db.Column(db.Float)
    away_point = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, server_default=func.current_timestamp())


class HistoricalOdds(db.Model):
    __tablename__ = "historical_odds"
    __table_args__ = (
        db.UniqueConstraint("game_date", "home_team", "away_team", "bookmaker"),
        db.Index("idx_historical_odds_lookup", "game_date", "home_team", "away_team"),
        db.Index("idx_historical_odds_season", "season"),
    )

    id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.String)
    game_id = db.Column(db.String)
    game_date = db.Column(db.String, nullable=False)
    home_team = db.Column(db.String, nullable=False)
    away_team = db.Column(db.String, nullable=False)
    bookmaker = db.Column(db.String, nullable=False)
    home_open_price = db.Column(db.Float)
    away_open_price = db.Column(db.Float)
    home_close_price = db.Column(db.Float)
    away_close_price = db.Column(db.Float)
    home_open_spread = db.Column(db.Float)
    away_open_spread = db.Column(db.Float)
    home_close_spread = db.Column(db.Float)
    away_close_spread = db.Column(db.Float)
    total_open = db.Column(db.Float)
    total_close = db.Column(db.Float)
    source_file = db.Column(db.String)
    imported_at = db.Column(db.DateTime, server_default=func.current_timestamp())


class LiveGameState(db.Model):
    __tablename__ = "live_game_state"
    __table_args__ = (
        db.Index("idx_live_game_last_updated", "last_updated"),
        db.Index("idx_live_game_seconds_remaining", "seconds_remaining"),
    )

    game_id = db.Column(db.String, primary_key=True)
    home_team = db.Column(db.String, nullable=False)
    away_team = db.Column(db.String, nullable=False)
    commence_time = db.Column(db.String)
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    quarter = db.Column(db.String)
    time_remaining_str = db.Column(db.String)
    seconds_remaining = db.Column(db.Integer)
    live_home_price = db.Column(db.Float)
    live_home_point = db.Column(db.Float)
    last_updated = db.Column(db.DateTime, server_default=func.current_timestamp())


class MarketSignal(db.Model):
    __tablename__ = "market_signals"

    id = db.Column(db.Integer, primary_key=True)
    signal_type = db.Column(db.String, nullable=False)
    game_id = db.Column(db.String)
    team = db.Column(db.String)
    description = db.Column(db.String, nullable=False)
    magnitude = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, server_default=func.current_timestamp())


class FuturesHistory(db.Model):
    __tablename__ = "futures_history"

    id = db.Column(db.Integer, primary_key=True)
    market = db.Column(db.String, nullable=False)
    team = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)
    points = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, server_default=func.current_timestamp())


class TeamGameLog(db.Model):
    __tablename__ = "team_game_logs"
    __table_args__ = (
        db.UniqueConstraint("season", "game_id", "team_abbr"),
        db.Index("idx_team_logs_team_date", "team_abbr", "game_date"),
        db.Index("idx_team_logs_season", "season"),
    )

    id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.String, nullable=False)
    game_id = db.Column(db.String, nullable=False)
    game_date = db.Column(db.String, nullable=False)
    team_abbr = db.Column(db.String, nullable=False)
    matchup = db.Column(db.String)
    wl = db.Column(db.String)
    pts = db.Column(db.Float)
    opp_pts = db.Column(db.Float)
    pace = db.Column(db.Float)
    efg_pct = db.Column(db.Float)
    tov_pct = db.Column(db.Float)
    off_rating = db.Column(db.Float)
    def_rating = db.Column(db.Float)
    net_rating = db.Column(db.Float)
    source = db.Column(db.String, server_default="TeamGameLogs")
    timestamp = db.Column(db.DateTime, server_default=func.current_timestamp())


class PlayerPosition(db.Model):
    __tablename__ = "player_positions"
    __table_args__ = (db.Index("idx_player_positions_team", "team_abbr"),)

    player_id = db.Column(db.Integer, primary_key=True)
    team_abbr = db.Column(db.String, nullable=False)
    position = db.Column(db.String, nullable=False)
    player_name = db.Column(db.String)
    timestamp = db.Column(db.DateTime, server_default=func.current_timestamp())


class OpponentDefenseMatrix(db.Model):
    __tablename__ = "opponent_defense_matrix"
    __table_args__ = (
        db.PrimaryKeyConstraint("team_abbr", "position", "stat"),
        db.Index("idx_opp_defense_lookup", "team_abbr", "position", "stat"),
    )

    team_abbr = db.Column(db.String, nullable=False)
    position = db.Column(db.String, nullable=False)
    stat = db.Column(db.String, nullable=False)
    modifier = db.Column(db.Float, nullable=False)
    sample_size = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, server_default=func.current_timestamp())


class PlayerBaseline(db.Model):
    __tablename__ = "player_baselines"
    __table_args__ = (
        db.PrimaryKeyConstraint("player_id", "stat"),
        db.Index("idx_player_baselines_player", "player_id"),
    )

    player_id = db.Column(db.Integer, nullable=False)
    stat = db.Column(db.String, nullable=False)
    per_minute_rate = db.Column(db.Float, nullable=False)
    projected_minutes = db.Column(db.Float, nullable=False)
    sample_size = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, server_default=func.current_timestamp())


class RefereeGameLog(db.Model):
    __tablename__ = "referee_game_logs"
    __table_args__ = (
        db.PrimaryKeyConstraint("game_id", "official_id"),
        db.Index("idx_ref_game_logs_official", "official_id"),
        db.Index("idx_ref_game_logs_date", "game_date"),
    )

    game_id = db.Column(db.String, nullable=False)
    official_id = db.Column(db.Integer, nullable=False)
    official_name = db.Column(db.String, nullable=False)
    game_date = db.Column(db.String)
    home_team = db.Column(db.String)
    away_team = db.Column(db.String)
    home_win = db.Column(db.Integer)
    total_points = db.Column(db.Float)
    total_fouls = db.Column(db.Float)
    updated_at = db.Column(db.DateTime, server_default=func.current_timestamp())


class RefereeStat(db.Model):
    __tablename__ = "referee_stats"

    official_id = db.Column(db.Integer, primary_key=True)
    official_name = db.Column(db.String, nullable=False)
    games_officiated = db.Column(db.Integer, default=0)
    home_win_pct = db.Column(db.Float, default=0.5)
    avg_total_points = db.Column(db.Float, default=0.0)
    avg_fouls_called = db.Column(db.Float, default=0.0)
    over_index = db.Column(db.Float, default=0.0)
    home_bias = db.Column(db.Float, default=0.0)
    last_game_date = db.Column(db.String)
    updated_at = db.Column(db.DateTime, server_default=func.current_timestamp())


class DailyInjury(db.Model):
    __tablename__ = "daily_injuries"
    __table_args__ = (
        db.Index("idx_daily_injuries_date", "date"),
        db.Index("idx_daily_injuries_team_date", "team_abbr", "date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, nullable=False)
    player_name = db.Column(db.String, nullable=False)
    team_abbr = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    vorp = db.Column(db.Float, default=0.0)


class TeamInjuryImpact(db.Model):
    __tablename__ = "team_injury_impact"
    __table_args__ = (
        db.UniqueConstraint("date", "team_abbr"),
        db.Index("idx_team_injury_impact_date", "date"),
        db.Index("idx_team_injury_impact_team_date", "team_abbr", "date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, nullable=False)
    team_abbr = db.Column(db.String, nullable=False)
    total_vorp_missing = db.Column(db.Float, default=0.0)
    injury_modifier = db.Column(db.Float, default=0.0)


class TeamInjuryStatus(db.Model):
    __tablename__ = "team_injury_status"
    __table_args__ = (
        db.PrimaryKeyConstraint("game_id", "team_abbr"),
        db.Index("idx_team_injury_date", "game_date"),
        db.Index("idx_team_injury_team_date", "team_abbr", "game_date"),
    )

    game_id = db.Column(db.String, nullable=False)
    team_abbr = db.Column(db.String, nullable=False)
    game_date = db.Column(db.String)
    inactive_player_ids = db.Column(db.String)
    inactive_player_names = db.Column(db.String)
    expected_value = db.Column(db.Float)
    active_value = db.Column(db.Float)
    injury_impact = db.Column(db.Float)
    updated_at = db.Column(db.DateTime, server_default=func.current_timestamp())
