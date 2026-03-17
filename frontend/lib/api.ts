import type {
  AnalysisAveragesResult,
  AnalysisCombinationResult,
  AnalysisProbabilityResult,
  AnalysisProbabilityTableResult,
  BacktestGameInput,
  BacktestResult,
  DashboardGame,
  EloRatings,
  FuturesRow,
  LiveGame,
  MarketOddsResponse,
  MarketSignal,
  PlayerCareerStat,
  PlayerGameLog,
  PlayerSearchResult,
  PredictionResponse,
  PropsResult,
  SimplePropProbability,
  TeamOption,
  TrainModelsResult,
} from "@/lib/types";

type QueryPrimitive = string | number | boolean | null | undefined;

function toQuery(params: Record<string, QueryPrimitive>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function parseError(response: Response) {
  try {
    const body = await response.json();
    if (typeof body?.error === "string") {
      return body.error;
    }
  } catch {}
  return `${response.status} ${response.statusText}`;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json() as Promise<T>;
}

export function getDashboard(date?: string) {
  return apiFetch<DashboardGame[]>(`/api/predictions/dashboard${toQuery({ date })}`);
}

export function getEloRatings() {
  return apiFetch<EloRatings>("/api/predictions/elo");
}

export function getPrediction(params: {
  gameId: string;
  home: string;
  away: string;
  date: string;
}) {
  return apiFetch<PredictionResponse>(
    `/api/predictions/game${toQuery({
      game_id: params.gameId,
      home: params.home,
      away: params.away,
      date: params.date,
    })}`,
  );
}

export function getLiveGames() {
  return apiFetch<LiveGame[]>("/api/live/games");
}

export function getMarketSurges() {
  return apiFetch<MarketSignal[]>("/api/market/surges");
}

export function getGameMarketOdds(gameId: string) {
  return apiFetch<MarketOddsResponse>(`/api/market/odds/${gameId}`);
}

export function getFutures() {
  return apiFetch<FuturesRow[]>("/api/market/futures");
}

export function searchPlayers(query: string) {
  return apiFetch<PlayerSearchResult[]>(`/api/players/search${toQuery({ q: query })}`);
}

export function getTeams() {
  return apiFetch<TeamOption[]>("/api/players/teams");
}

export function getAdvancedProp(params: {
  playerId: number;
  stat: string;
  line: number;
  opponent: string;
  date?: string;
}) {
  return apiFetch<PropsResult>(
    `/api/predictions/props/advanced${toQuery({
      player_id: params.playerId,
      stat: params.stat,
      line: params.line,
      opponent: params.opponent,
      date: params.date,
    })}`,
  );
}

export function getSimplePropProbability(params: {
  playerId: number;
  stat: string;
  line: number;
  numGames?: number;
}) {
  return apiFetch<SimplePropProbability>(
    `/api/predictions/player-props${toQuery({
      player_id: params.playerId,
      stat: params.stat,
      line: params.line,
      num_games: params.numGames,
    })}`,
  );
}

export function getAnalysisProbability(payload: {
  player_id?: number;
  logs?: Record<string, unknown>[];
  ast?: number;
  reb?: number;
  pts?: number;
  stl?: number;
  blk?: number;
  pf?: number;
  threes_made?: number;
  triple_double?: boolean;
  double_double?: boolean;
  win?: boolean;
}) {
  return apiFetch<AnalysisProbabilityResult>("/api/analysis/probability", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAnalysisCombination(payload: {
  player_ids: number[];
  players: Array<Record<string, number>>;
  combine?: "all" | "pra" | "sb";
}) {
  return apiFetch<AnalysisCombinationResult>("/api/analysis/combination", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAnalysisProbabilityTable(payload: {
  player_ids: number[];
  cats?: string[];
  graph_size?: number;
}) {
  return apiFetch<AnalysisProbabilityTableResult>("/api/analysis/probability-table", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAnalysisAverages(payload: {
  logs: Record<string, unknown>[];
  cats?: string[];
}) {
  return apiFetch<AnalysisAveragesResult>("/api/analysis/averages", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPlayerCareer(playerId: number) {
  return apiFetch<PlayerCareerStat[]>(`/api/stats/player/${playerId}/career`);
}

export function getPlayerGameLogs(params: {
  playerId: number;
  numGames?: number;
  seasons?: string;
}) {
  return apiFetch<PlayerGameLog[]>(
    `/api/stats/player/${params.playerId}/gamelogs${toQuery({
      num_games: params.numGames,
      seasons: params.seasons,
    })}`,
  );
}

export function trainModels(payload?: { seasons?: string[] }) {
  return apiFetch<TrainModelsResult>("/api/predictions/train", {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export function runBacktest(payload: {
  games?: BacktestGameInput[];
  starting_bankroll: number;
  kelly_fraction?: number;
  seasons?: string[];
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  return apiFetch<BacktestResult>("/api/predictions/backtest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
