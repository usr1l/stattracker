"use client";

import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Orbit,
  Radar,
  TrendingUp,
} from "lucide-react";

import { getDashboard, getEloRatings, trainModels } from "@/lib/api";
import { formatPercent, formatSignedNumber } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MetricCard } from "@/components/metric-card";
import { PageHero } from "@/components/page-hero";
import { SectionHeader } from "@/components/section-header";
import { StatusMessage } from "@/components/status-message";

const FEATURE_LABELS: Record<string, string> = {
  elo_diff: "ELO gap",
  net_rating_diff: "Net rating gap",
  home_distance_traveled: "Home travel drag",
  away_distance_traveled: "Away travel drag",
  home_injury_impact: "Home injury drag",
  away_injury_impact: "Away injury drag",
  ref_home_bias: "Ref home bias",
  ref_total_bias: "Ref total bias",
};

function featureLabel(feature: string) {
  return FEATURE_LABELS[feature] ?? feature.replace(/_/g, " ");
}

export default function HomePage() {
  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => getDashboard(),
  });
  const eloQuery = useQuery({
    queryKey: ["elo-ratings"],
    queryFn: () => getEloRatings(),
  });
  const trainMutation = useMutation({
    mutationFn: () => trainModels(),
  });

  const games = (dashboardQuery.data ?? []).filter((game) => !game.error);
  const topEdgeGame = [...games]
    .filter((game) => typeof game.edge === "number")
    .sort((left, right) => Math.abs(right.edge ?? 0) - Math.abs(left.edge ?? 0))[0];
  const eloLeaders = Object.entries(eloQuery.data ?? {})
    .sort((left, right) => right[1] - left[1])
    .slice(0, 6);
  const trackedSignals = games.reduce((count, game) => count + (game.market_signals?.length ?? 0), 0);

  return (
    <div className="flex flex-col gap-5">
      <PageHero
        eyebrow="Command Board"
        title="Model board, market read, and training controls in one darker pass."
        description="The home route is now the operator view: scan the slate, inspect the strongest edge, watch the ELO ladder, and trigger a retrain without leaving the dashboard."
        actions={
          <>
            <Button asChild variant="outline">
              <Link href="/live">
                Open live board
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button
              type="button"
              onClick={() => trainMutation.mutate()}
              disabled={trainMutation.isPending}
            >
              <BrainCircuit className="size-4" />
              {trainMutation.isPending ? "Training..." : "Train models"}
            </Button>
          </>
        }
        statusLabel="Operator"
      />

      <section className="grid gap-4 xl:grid-cols-4">
        <MetricCard
          label="Games on Board"
          value={dashboardQuery.isLoading ? "..." : String(games.length)}
          hint="Scoreboard-backed slate for the selected date."
          icon={<Activity className="size-5 text-sky-300" />}
        />
        <MetricCard
          label="Best Current Edge"
          value={dashboardQuery.isLoading ? "..." : formatPercent(topEdgeGame?.edge, 1)}
          hint={topEdgeGame ? `${topEdgeGame.away_team} @ ${topEdgeGame.home_team}` : "Awaiting market prices."}
          icon={<TrendingUp className="size-5 text-emerald-300" />}
          tone="positive"
        />
        <MetricCard
          label="Signal Events"
          value={dashboardQuery.isLoading ? "..." : String(trackedSignals)}
          hint="Tracked market_signals across the live slate."
          icon={<Radar className="size-5 text-indigo-200" />}
        />
        <MetricCard
          label="ELO Leader"
          value={eloQuery.isLoading ? "..." : (eloLeaders[0]?.[0] ?? "N/A")}
          hint={eloLeaders[0] ? `${eloLeaders[0][1].toFixed(0)} rating` : "Current rating ladder."}
          icon={<Orbit className="size-5 text-sky-300" />}
        />
      </section>

      {trainMutation.data ? (
        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-5">
            <div>
              <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">Training</p>
              <p className="mt-2 text-sm text-slate-300">
                {trainMutation.data.ok
                  ? "Training pipeline finished successfully."
                  : trainMutation.data.error || "Training request returned without an ok flag."}
              </p>
            </div>
            <Badge variant={trainMutation.data.ok ? "positive" : "negative"}>
              {trainMutation.data.ok ? "Completed" : "Needs attention"}
            </Badge>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Slate"
              title="Tonight’s prediction board"
              description="Cleaner board layout with direct links into matchup detail and tighter emphasis on the actual decision fields."
            />
          </CardHeader>
          <CardContent>
            {dashboardQuery.isLoading ? (
              <StatusMessage
                title="Loading board"
                body="Pulling the scoreboard-backed dashboard feed from the backend."
              />
            ) : dashboardQuery.error ? (
              <StatusMessage
                title="Board unavailable"
                body={(dashboardQuery.error as Error).message}
              />
            ) : games.length === 0 ? (
              <StatusMessage
                title="No scheduled games returned"
                body="The backend did not return any active scoreboard rows for the selected date."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Matchup</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Win %</TableHead>
                    <TableHead>Spread</TableHead>
                    <TableHead>Total</TableHead>
                    <TableHead>Market</TableHead>
                    <TableHead>Edge</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {games.map((game) => {
                    const edgeVariant =
                      (game.edge ?? 0) > 0 ? "positive" : (game.edge ?? 0) < 0 ? "negative" : "default";

                    return (
                      <TableRow key={game.game_id}>
                        <TableCell className="min-w-[220px]">
                          <Link
                            href={{
                              pathname: `/game/${game.game_id}`,
                              query: {
                                home: game.home_team,
                                away: game.away_team,
                                date: game.date,
                              },
                            }}
                            className="group flex flex-col gap-1"
                          >
                            <span className="text-base font-semibold text-slate-50 transition-colors group-hover:text-sky-300">
                              {game.away_team} @ {game.home_team}
                            </span>
                            <span className="text-sm text-slate-500">
                              {(game.away_name ?? game.away_team)} at {(game.home_name ?? game.home_team)}
                            </span>
                          </Link>
                        </TableCell>
                        <TableCell className="text-slate-400">{game.status || "Scheduled"}</TableCell>
                        <TableCell>{formatPercent(game.model?.home_win_prob, 1)}</TableCell>
                        <TableCell>{formatSignedNumber(game.model?.projected_spread, 1)}</TableCell>
                        <TableCell>{game.model?.projected_total?.toFixed(1) ?? "N/A"}</TableCell>
                        <TableCell className="text-slate-400">
                          {game.market?.spread !== null && game.market?.spread !== undefined
                            ? `${formatSignedNumber(game.market.spread, 1)} / ${game.market.total?.toFixed(1) ?? "N/A"}`
                            : "Awaiting odds"}
                        </TableCell>
                        <TableCell>
                          <Badge variant={edgeVariant}>{formatPercent(game.edge, 1)}</Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-5">
          <Card>
            <CardHeader>
              <SectionHeader
                eyebrow="Focus"
                title={topEdgeGame ? `${topEdgeGame.away_team} @ ${topEdgeGame.home_team}` : "No top edge yet"}
                description="Most actionable current edge on the board, with the strongest drivers visible immediately."
              />
            </CardHeader>
            <CardContent className="space-y-4">
              {!topEdgeGame ? (
                <StatusMessage
                  title="No edge candidate"
                  body="As soon as the dashboard returns a priced game, the strongest one will land here."
                />
              ) : (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <MetricCard
                      label="Home win"
                      value={formatPercent(topEdgeGame.model?.home_win_prob, 1)}
                      hint="Model probability on the home side."
                    />
                    <MetricCard
                      label="Edge"
                      value={formatPercent(topEdgeGame.edge, 1)}
                      hint={`${topEdgeGame.market_signals?.length ?? 0} signal events attached.`}
                      tone="positive"
                    />
                  </div>
                  <div className="grid gap-3">
                    {(topEdgeGame.model?.top_features ?? []).map((driver) => (
                      <div
                        key={`${topEdgeGame.game_id}-${driver.feature}`}
                        className="rounded-[22px] border border-white/8 bg-white/4 p-4"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                            {featureLabel(driver.feature)}
                          </p>
                          <Badge variant="accent">{formatPercent(driver.game_impact, 0)} impact</Badge>
                        </div>
                        <p className="mt-2 text-sm text-slate-300">
                          Importance {formatPercent(driver.importance, 1)} with current value{" "}
                          <span className="text-slate-50">{driver.value}</span>.
                        </p>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <SectionHeader
                eyebrow="ELO"
                title="Current power ladder"
                description="Pulled directly from the `/api/predictions/elo` endpoint."
              />
            </CardHeader>
            <CardContent className="space-y-3">
              {eloQuery.isLoading ? (
                <StatusMessage title="Loading ELO ladder" body="Fetching team ratings from the backend." />
              ) : eloQuery.error ? (
                <StatusMessage title="ELO unavailable" body={(eloQuery.error as Error).message} />
              ) : (
                eloLeaders.map(([team, rating], index) => (
                  <div
                    key={team}
                    className="flex items-center justify-between rounded-[20px] border border-white/8 bg-white/4 px-4 py-3"
                  >
                    <div>
                      <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                        Rank {index + 1}
                      </p>
                      <p className="mt-1 text-lg font-semibold text-slate-50">{team}</p>
                    </div>
                    <Badge variant={index < 3 ? "positive" : "default"}>{rating.toFixed(0)}</Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
