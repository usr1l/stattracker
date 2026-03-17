export type PredictionFeatureDriver = {
  feature: string;
  importance: number;
  game_impact: number;
  value: number;
  impact?: "High" | "Medium" | "Low";
};

export type DashboardGame = {
  game_id: string;
  date: string;
  status: string;
  home_team: string;
  away_team: string;
  home_name?: string;
  away_name?: string;
  model?: {
    home_win_prob?: number | null;
    projected_spread?: number | null;
    projected_total?: number | null;
    top_features?: PredictionFeatureDriver[];
    model_source?: {
      win_prob?: string;
      spread?: string;
      total?: string;
    };
  };
  market?: {
    home_price?: number | null;
    away_price?: number | null;
    spread?: number | null;
    total?: number | null;
    implied_home_prob?: number | null;
  };
  edge?: number | null;
  trend_flags?: {
    home?: string[];
    away?: string[];
  };
  market_signals?: Array<{
    type: string;
    team?: string | null;
    desc: string;
  }>;
  error?: string;
};

export type EloRatings = Record<string, number>;

export type PredictionResponse = {
  matchup: {
    home: string;
    away: string;
    date: string;
  };
  key_drivers: PredictionFeatureDriver[];
  projections: {
    home_win_prob: number;
    projected_spread: number;
    projected_total: number;
    top_features: PredictionFeatureDriver[];
    model_source?: {
      win_prob?: string;
      spread?: string;
      total?: string;
    };
  };
  features_snapshot: {
    elo: {
      elo_diff: number;
    };
    stats: {
      net_rating_diff: number;
      home_net_rating_l10: number;
      away_net_rating_l10: number;
      home_pace_l10: number;
      away_pace_l10: number;
    };
    schedule: {
      home_rest_days: number;
      away_rest_days: number;
      home_b2b: number;
      away_b2b: number;
      home_distance_traveled: number;
      away_distance_traveled: number;
    };
    context: {
      ref_home_bias: number;
      ref_total_bias: number;
      ref_foul_bias: number;
      home_injury_impact: number;
      away_injury_impact: number;
      assigned_referees?: string[];
      home_inactive_count?: number;
      away_inactive_count?: number;
      home_inactive_players?: string[];
      away_inactive_players?: string[];
    };
  };
  trends: {
    home: string[];
    away: string[];
  };
  market_signals: Array<{
    type: string;
    team?: string | null;
    desc: string;
  }>;
};

export type LiveGame = {
  game_id: string;
  matchup: string;
  score: {
    home: number;
    away: number;
  };
  clock: string;
  model: {
    pre_game_prob?: number | null;
    score_state_prob?: number | null;
    time_weight?: number | null;
    live_prob?: number | null;
  };
  market: {
    live_home_price?: number | null;
    live_implied_prob?: number | null;
    live_spread?: number | null;
  };
  edge?: number | null;
};

export type MarketSignal = {
  signal_type: string;
  game_id?: string | null;
  team?: string | null;
  description: string;
  magnitude?: number | null;
  timestamp: string;
};

export type MarketOddsSnapshot = {
  market_type?: string;
  home_price?: number | null;
  away_price?: number | null;
  home_point?: number | null;
  away_point?: number | null;
  timestamp?: string;
};

export type MarketOddsResponse = {
  current_line: MarketOddsSnapshot;
  history: MarketOddsSnapshot[];
  movement_total: number;
};

export type FuturesRow = {
  market: string;
  team: string;
  price: number;
  timestamp: string;
};

export type PlayerSearchResult = {
  PERSON_ID: number;
  DISPLAY_FIRST_LAST: string;
  TEAM_ABBREVIATION?: string;
};

export type TeamOption = {
  id: number;
  full_name: string;
  abbreviation: string;
};

export type PropsResult = {
  player_id: number;
  stat: string;
  sportsbook_line: number;
  projected_line: number;
  modifiers_applied: {
    base_projection: number;
    opponent_defense_mod: number;
    pace_mod: number;
  };
  edge_value: number;
  recommended_bet: "OVER" | "UNDER" | "PASS";
};

export type SimplePropProbability = {
  player_id: number;
  stat: string;
  line: number;
  line_threshold_integer: number;
  over_pct: number;
  sample_size: number;
  l10_avg: number;
  implied_prob_vs_line: number;
  criteria: string;
};

export type AnalysisProbabilityResult = {
  criteria: string;
  hit: number;
  total: number;
  percentage: string;
};

export type AnalysisCombinationResult = {
  result: string;
};

export type AnalysisProbabilityTableResult = {
  table: Record<string, Record<string, string>>;
};

export type AnalysisAveragesResult = Record<string, number>;

export type PlayerCareerStat = Record<string, string | number | null>;
export type PlayerGameLog = Record<string, string | number | boolean | null>;

export type TrainModelsResult = {
  ok?: boolean;
  error?: string;
  [key: string]: unknown;
};

export type BacktestGameInput = {
  date: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  home_odds: number;
  away_odds: number;
  model_home_prob: number;
  game_id?: string;
  home_open_price?: number;
  away_open_price?: number;
  home_close_price?: number;
  away_close_price?: number;
  home_open_spread?: number;
  away_open_spread?: number;
  home_close_spread?: number;
  away_close_spread?: number;
};

export type BacktestConfidenceBucket = {
  label: string;
  bets: number;
  pushes?: number;
  win_rate: number;
  average_model_prob: number;
  average_edge: number;
  roi_percent: number;
  calibration_gap: number;
  average_clv: number;
};

export type BacktestConfidenceTier = {
  label: string;
  bets: number;
  pushes?: number;
  win_rate: number;
  average_edge: number;
  roi_percent: number;
  average_clv: number;
};

export type BacktestFractionSweep = {
  kelly_fraction: number;
  ending_bankroll: number;
  roi_percent: number;
  max_drawdown: number;
  total_bets: number;
  win_rate: number;
  average_clv: number;
  score: number;
};

export type BacktestBetHistoryEntry = {
  index: number;
  date: string;
  matchup: string;
  side: string;
  result?: string;
  edge_pct: number;
  return_pct: number;
  bet_size: number;
  profit: number;
  clv_price?: number | null;
  clv_spread?: number | null;
};

export type BacktestResult = {
  games_processed: number;
  total_bets: number;
  wins: number;
  losses: number;
  pushes?: number;
  win_rate: number;
  starting_bankroll: number;
  ending_bankroll: number;
  roi_percent: number;
  max_drawdown: number;
  brier_score: number;
  average_edge: number;
  average_bet_size: number;
  average_clv: number;
  average_clv_spread: number;
  average_clv_implied_prob: number;
  clv_unit: string;
  kelly_fraction: number;
  recommended_kelly_fraction: number;
  confidence_buckets: BacktestConfidenceBucket[];
  confidence_tiers: BacktestConfidenceTier[];
  fraction_sweep: BacktestFractionSweep[];
  bet_history: BacktestBetHistoryEntry[];
  data_source?: string;
  bankroll_history: Array<{
    index: number;
    label: string;
    bankroll: number;
    bet_placed?: boolean;
  }>;
};
