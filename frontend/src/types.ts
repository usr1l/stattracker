export type TodayGame = {
  game_id: string;
  date: string;
  status: string;
  status_display?: string;
  state?: "pre" | "live" | "final";
  scoreboard_fetched_at?: string;
  home_team: string;
  away_team: string;
  home_name?: string;
  away_name?: string;
  home_logo_url?: string;
  away_logo_url?: string;
};

export type GameStatusDebug = {
  game_status_id?: number | null;
  game_status_text?: string | null;
  live_period?: number | null;
  live_pc_time?: string | null;
  live_period_time_bcast?: string | null;
  has_linescore?: boolean;
  has_points_data?: boolean;
};

export type TeamLeader = {
  name: string;
  value: number | null;
};

export type TeamLeaders = {
  points?: TeamLeader | null;
  rebounds?: TeamLeader | null;
  assists?: TeamLeader | null;
};

export type GameDetailTeam = {
  team_id: number;
  abbreviation: string;
  name: string;
  logo_url: string;
  score: number | null;
  record?: string | null;
  leaders?: TeamLeaders | null;
};

export type GameDetailLineScore = {
  label: string;
  home: number | null;
  away: number | null;
};

export type GameDetailStat = {
  label: string;
  home: string | number | null;
  away: string | number | null;
};

export type GameDetailBroadcasts = {
  national?: string | null;
  home?: string | null;
  away?: string | null;
};

export type GameDetailLastMeeting = {
  date: string;
  summary: string;
};

export type GameDetailSeries = {
  leader?: string | null;
  home_wins?: number | null;
  home_losses?: number | null;
};

export type GameDetail = {
  game_id: string;
  date: string;
  status: string;
  status_display?: string;
  state: "pre" | "live" | "final";
  scoreboard_fetched_at?: string;
  status_debug?: GameStatusDebug;
  arena?: string | null;
  broadcasts: GameDetailBroadcasts;
  home_team: GameDetailTeam;
  away_team: GameDetailTeam;
  linescore: GameDetailLineScore[];
  team_stats: GameDetailStat[];
  last_meeting?: GameDetailLastMeeting | null;
  series?: GameDetailSeries | null;
};
