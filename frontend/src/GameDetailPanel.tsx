import type { GameDetail, TodayGame } from "./types";

type GameDetailPanelProps = {
  game: TodayGame | null;
  detail: GameDetail | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
};

type TeamPanelProps = {
  abbreviation: string;
  name: string;
  logoUrl?: string;
  record?: string | null;
  score?: number | null;
  state?: GameDetail["state"];
};

function formatEasternDate(date: string) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(new Date(`${date}T12:00:00Z`));
}

function formatEasternTime(value?: string) {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(parsed);
}

function formatStatusHeadline(detail: GameDetail | null) {
  if (!detail) {
    return "Connecting";
  }
  if (detail.state === "pre") {
    return "Not yet started";
  }
  if (detail.state === "live") {
    return "Live";
  }
  return "Final";
}

function displayStatusLine(detail: GameDetail | null, game: TodayGame) {
  return detail?.status_display || detail?.status || game.status_display || game.status || "Scheduled";
}

function TeamPanel({ abbreviation, name, logoUrl, record, score, state }: TeamPanelProps) {
  return (
    <section className="detail-sheet__team-panel">
      <div className="detail-sheet__team-mark">
        {logoUrl ? <img src={logoUrl} alt="" loading="lazy" /> : <span>{abbreviation}</span>}
      </div>
      <div className="detail-sheet__team-copy">
        <p className="detail-sheet__team-abbr">{abbreviation}</p>
        <h3 className="detail-sheet__team-name">{name}</h3>
        <p className="detail-sheet__team-record">{record || "Season record unavailable"}</p>
      </div>
      <div className="detail-sheet__team-score" aria-label={`${abbreviation} score`}>
        {state === "pre" && score == null ? "—" : score ?? "—"}
      </div>
    </section>
  );
}

function ConnectionStatus({
  game,
  detail,
  loading,
  error,
}: {
  game: TodayGame;
  detail: GameDetail | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return (
      <section className="detail-sheet__status-card">
        <p className="detail-sheet__status-label">Connection</p>
        <p className="detail-sheet__status-title">Connecting to local backend…</p>
        <p className="detail-sheet__status-copy">
          The frontend expects /api requests to proxy to Flask on 127.0.0.1:5001.
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="detail-sheet__status-card detail-sheet__status-card--error">
        <p className="detail-sheet__status-label">Connection</p>
        <p className="detail-sheet__status-title">Backend connection failed</p>
        <p className="detail-sheet__status-copy">{error}</p>
        <p className="detail-sheet__status-copy">
          Local dev uses the Vite /api proxy to reach Flask on 127.0.0.1:5001. ngrok is not
          required.
        </p>
      </section>
    );
  }

  if (!detail) {
    return (
      <section className="detail-sheet__status-card">
        <p className="detail-sheet__status-label">Connection</p>
        <p className="detail-sheet__status-title">No detail available</p>
      </section>
    );
  }

  const fetchedAt = formatEasternTime(detail.scoreboard_fetched_at);
  const rawStatus = detail.status_debug?.game_status_text;

  return (
    <section className="detail-sheet__status-card">
      <p className="detail-sheet__status-label">Connection</p>
      <p className="detail-sheet__status-title">
        {detail.state === "pre"
          ? "Local backend is connected; the latest NBA scoreboard response is still pregame."
          : "Local backend is connected and returning live scoreboard data."}
      </p>
      <dl className="detail-sheet__status-list">
        <div>
          <dt>Displayed status</dt>
          <dd>{displayStatusLine(detail, game)}</dd>
        </div>
        <div>
          <dt>Last fetch</dt>
          <dd>{fetchedAt || "Unavailable"}</dd>
        </div>
        <div>
          <dt>Raw scoreboard status</dt>
          <dd>{rawStatus || detail.status || "Unavailable"}</dd>
        </div>
        <div>
          <dt>Live period</dt>
          <dd>{detail.status_debug?.live_period ?? "0"}</dd>
        </div>
      </dl>
    </section>
  );
}

export function GameDetailPanel({ game, detail, loading, error, onClose }: GameDetailPanelProps) {
  if (!game) {
    return null;
  }

  const awayTeam = detail?.away_team ?? {
    abbreviation: game.away_team,
    name: game.away_name || game.away_team,
    logo_url: game.away_logo_url || "",
    score: null,
    team_id: 0,
  };
  const homeTeam = detail?.home_team ?? {
    abbreviation: game.home_team,
    name: game.home_name || game.home_team,
    logo_url: game.home_logo_url || "",
    score: null,
    team_id: 0,
  };

  return (
    <div className="detail-sheet" role="dialog" aria-modal="true" aria-labelledby="game-detail-title">
      <button className="detail-sheet__backdrop" type="button" aria-label="Close game detail" onClick={onClose} />
      <aside className="detail-sheet__panel">
        <header className="detail-sheet__hero">
          <button className="detail-sheet__close" type="button" onClick={onClose}>
            Close
          </button>
          <div className="detail-sheet__hero-grid">
            <TeamPanel
              abbreviation={awayTeam.abbreviation}
              name={awayTeam.name}
              logoUrl={awayTeam.logo_url}
              record={awayTeam.record}
              score={awayTeam.score}
              state={detail?.state}
            />
            <div className="detail-sheet__hero-center">
              <p className="detail-sheet__hero-date">{formatEasternDate(game.date)}</p>
              <h2 className="detail-sheet__hero-title" id="game-detail-title">
                {awayTeam.name} at {homeTeam.name}
              </h2>
              <p className="detail-sheet__hero-status">{formatStatusHeadline(detail)}</p>
              <p className="detail-sheet__hero-substatus">{displayStatusLine(detail, game)}</p>
            </div>
            <TeamPanel
              abbreviation={homeTeam.abbreviation}
              name={homeTeam.name}
              logoUrl={homeTeam.logo_url}
              record={homeTeam.record}
              score={homeTeam.score}
              state={detail?.state}
            />
          </div>
        </header>

        <div className="detail-sheet__body">
          <ConnectionStatus game={game} detail={detail} loading={loading} error={error} />
        </div>
      </aside>
    </div>
  );
}
