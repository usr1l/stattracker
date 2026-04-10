import { useEffect, useMemo, useState } from "react";

import { ApiError, getGameDetail, getTodayGames } from "./api";
import { GameDetailPanel } from "./GameDetailPanel";
import type { GameDetail, TodayGame } from "./types";

const SLATE_REFRESH_INTERVAL_MS = 60_000;
const DETAIL_REFRESH_INTERVAL_MS = 30_000;

function formatEasternLabel(date?: string) {
  const source = date ? new Date(`${date}T12:00:00Z`) : new Date();
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(source);
}

function gameAriaLabel(game: TodayGame) {
  const away = game.away_name || game.away_team;
  const home = game.home_name || game.home_team;
  return `Open ${away} at ${home}, ${displayGameStatus(game)}`;
}

function displayGameStatus(game: Pick<TodayGame, "status" | "status_display">) {
  return game.status_display || game.status || "Scheduled";
}

type TeamBadgeProps = {
  abbreviation: string;
  name?: string;
  logoUrl?: string;
};

function TeamBadge({ abbreviation, name, logoUrl }: TeamBadgeProps) {
  const [showLogo, setShowLogo] = useState(Boolean(logoUrl));
  const label = name || abbreviation;

  return (
    <div className="game-card__team">
      <span
        className={`game-card__team-logo${showLogo ? "" : " game-card__team-logo--fallback"}`}
        aria-hidden="true"
      >
        {showLogo && logoUrl ? (
          <img
            src={logoUrl}
            alt=""
            loading="lazy"
            onError={() => {
              setShowLogo(false);
            }}
          />
        ) : (
          abbreviation
        )}
      </span>
      <span className="game-card__team-name">{label}</span>
    </div>
  );
}

export default function App() {
  const [games, setGames] = useState<TodayGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedGame, setSelectedGame] = useState<TodayGame | null>(null);
  const [selectedGameDetail, setSelectedGameDetail] = useState<GameDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadGames(showSpinner = false) {
      if (showSpinner) {
        setLoading(true);
      }
      setError(null);

      try {
        const nextGames = await getTodayGames();
        if (!cancelled) {
          setGames(nextGames);
        }
      } catch (loadError) {
        if (!cancelled) {
          setGames([]);
          setError(
            loadError instanceof ApiError || loadError instanceof Error
              ? loadError.message
              : "Unable to load today's slate.",
          );
        }
      } finally {
        if (!cancelled && showSpinner) {
          setLoading(false);
        }
      }
    }

    loadGames(true);

    const refreshId = window.setInterval(() => {
      void loadGames();
    }, SLATE_REFRESH_INTERVAL_MS);

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        void loadGames();
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      cancelled = true;
      window.clearInterval(refreshId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const easternLabel = useMemo(() => formatEasternLabel(games[0]?.date), [games]);

  useEffect(() => {
    if (!selectedGame) {
      setSelectedGameDetail(null);
      setDetailLoading(false);
      setDetailError(null);
      return;
    }

    const gameToLoad = selectedGame;
    let cancelled = false;

    setSelectedGameDetail(null);

    async function loadGameDetail(showSpinner = false) {
      if (showSpinner) {
        setDetailLoading(true);
      }

      try {
        const nextDetail = await getGameDetail(gameToLoad.game_id, gameToLoad.date);
        if (!cancelled) {
          setSelectedGameDetail(nextDetail);
          setDetailError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setDetailError(
            loadError instanceof ApiError || loadError instanceof Error
              ? loadError.message
              : "Unable to load game detail.",
          );
        }
      } finally {
        if (!cancelled && showSpinner) {
          setDetailLoading(false);
        }
      }
    }

    void loadGameDetail(true);

    const refreshId = window.setInterval(() => {
      void loadGameDetail();
    }, DETAIL_REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(refreshId);
    };
  }, [selectedGame]);

  return (
    <div className="app">
      <header className="navbar">
        <a className="navbar__brand" href="/">
          StatTracker
        </a>
        <p className="navbar__date">{easternLabel}</p>
      </header>

      <main className="app__main">
        {loading ? (
          <div className="state-card">
            <p className="state-card__title">Loading schedule…</p>
          </div>
        ) : error ? (
          <div className="state-card state-card--error">
            <p className="state-card__title">Couldn&apos;t load games</p>
            <p className="state-card__detail">{error}</p>
          </div>
        ) : games.length === 0 ? (
          <div className="state-card">
            <p className="state-card__title">No games today</p>
          </div>
        ) : (
          <ol className="slate-grid" aria-label="Today's NBA games">
            {games.map((game) => (
              <li key={game.game_id}>
                <button
                  type="button"
                  className="game-card game-card--button"
                  aria-label={gameAriaLabel(game)}
                  onClick={() => {
                    setSelectedGame(game);
                  }}
                >
                  <div className="game-card__row">
                    <TeamBadge
                      abbreviation={game.away_team}
                      name={game.away_name}
                      logoUrl={game.away_logo_url}
                    />
                    <span className="game-card__at">@</span>
                    <TeamBadge
                      abbreviation={game.home_team}
                      name={game.home_name}
                      logoUrl={game.home_logo_url}
                    />
                  </div>
                  <div className="game-card__footer">
                    <p className="game-card__status">{displayGameStatus(game)}</p>
                    <span className="game-card__action">Open Game</span>
                  </div>
                </button>
              </li>
            ))}
          </ol>
        )}
      </main>

      <GameDetailPanel
        game={selectedGame}
        detail={selectedGameDetail}
        loading={detailLoading}
        error={detailError}
        onClose={() => {
          setSelectedGame(null);
        }}
      />
    </div>
  );
}
