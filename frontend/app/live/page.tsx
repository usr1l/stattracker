"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, TimerReset, TrendingUp, Waves } from "lucide-react";

import { getLiveGames } from "@/lib/api";
import { formatPercent, formatSignedNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { MetricCard } from "@/components/metric-card";
import { PageHero } from "@/components/page-hero";
import { SectionHeader } from "@/components/section-header";
import { StatusMessage } from "@/components/status-message";

export default function LivePage() {
  const liveQuery = useQuery({
    queryKey: ["live-games"],
    queryFn: () => getLiveGames(),
    refetchInterval: 30_000,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });

  const games = liveQuery.data ?? [];
  const topEdge = [...games].sort((a, b) => Math.abs(b.edge ?? 0) - Math.abs(a.edge ?? 0))[0];

  return (
    <div className="flex flex-col gap-5">
      <PageHero
        eyebrow="Live Edge"
        title="Pregame conviction and score-state reality blended in real time."
        description="The live route keeps polling in the background every 30 seconds while the backend refreshes on a slower cadence. The surface is simpler now, but it exposes the blend math instead of hiding it."
        statusLabel="Polling"
      />

      <section className="grid gap-4 xl:grid-cols-4">
        <MetricCard
          label="Active Games"
          value={liveQuery.isLoading ? "..." : String(games.length)}
          hint="Current stored live states with remaining game clock."
          icon={<Activity className="size-5 text-sky-300" />}
        />
        <MetricCard
          label="Top Live Edge"
          value={liveQuery.isLoading ? "..." : formatPercent(topEdge?.edge, 1)}
          hint={topEdge?.matchup ?? "Waiting for a live board."}
          icon={<TrendingUp className="size-5 text-emerald-300" />}
          tone="positive"
        />
        <MetricCard
          label="UI Refresh"
          value="30s"
          hint="React Query refetch interval."
          icon={<TimerReset className="size-5 text-indigo-200" />}
        />
        <MetricCard
          label="Top Clock"
          value={topEdge?.clock ?? "Live"}
          hint="Most actionable game clock snapshot."
          icon={<Waves className="size-5 text-sky-300" />}
        />
      </section>

      <Card>
        <CardHeader>
          <SectionHeader
            eyebrow="Board"
            title="Current live opportunities"
            description="Positive edge means the model is more bullish on the home side than the live market price implies."
          />
        </CardHeader>
        <CardContent>
          {liveQuery.isLoading ? (
            <StatusMessage title="Waiting for live state" body="Polling the backend for active in-game state and pricing." />
          ) : liveQuery.error ? (
            <StatusMessage title="Live feed unavailable" body={(liveQuery.error as Error).message} />
          ) : games.length === 0 ? (
            <StatusMessage title="No live games detected" body="When the backend stores active snapshots, the in-game edge board will populate here." />
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {games.map((game) => {
                const variant =
                  (game.edge ?? 0) > 0 ? "positive" : (game.edge ?? 0) < 0 ? "negative" : "default";
                return (
                  <Card key={game.game_id} className="overflow-hidden">
                    <CardContent className="grid gap-5 p-6">
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div>
                          <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                            {game.clock}
                          </p>
                          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
                            {game.matchup}
                          </h3>
                          <p className="mt-1 text-sm text-slate-400">
                            Score {game.score.away} - {game.score.home}
                          </p>
                        </div>
                        <Badge variant={variant}>{formatPercent(game.edge, 1)} edge</Badge>
                      </div>

                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        <MetricCard
                          label="Pregame"
                          value={formatPercent(game.model.pre_game_prob, 1)}
                          hint="Base probability before tip."
                        />
                        <MetricCard
                          label="Score State"
                          value={formatPercent(game.model.score_state_prob, 1)}
                          hint="Margin-only probability estimate."
                        />
                        <MetricCard
                          label="Time Weight"
                          value={formatPercent(game.model.time_weight, 0)}
                          hint="Pregame influence still retained."
                        />
                        <MetricCard
                          label="Live Model"
                          value={formatPercent(game.model.live_prob, 1)}
                          hint="Blended live probability."
                        />
                        <MetricCard
                          label="Live Price"
                          value={game.market.live_home_price?.toFixed(2) ?? "N/A"}
                          hint="Home-side live decimal price."
                        />
                        <MetricCard
                          label="Live Spread"
                          value={formatSignedNumber(game.market.live_spread, 1)}
                          hint={`Market implied ${formatPercent(game.market.live_implied_prob, 1)}.`}
                        />
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
