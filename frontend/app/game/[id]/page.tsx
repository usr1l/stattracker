"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Activity, Gauge, Scale, Target, Waves } from "lucide-react";

import { getDashboard, getGameMarketOdds, getPrediction } from "@/lib/api";
import { formatPercent, formatSignedNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MetricCard } from "@/components/metric-card";
import { ModelDriversPanel } from "@/components/model-drivers-panel";
import { PageHero } from "@/components/page-hero";
import { SectionHeader } from "@/components/section-header";
import { StatusMessage } from "@/components/status-message";

const FEATURE_LABELS: Record<string, string> = {
  elo_diff: "ELO gap",
  net_rating_diff: "Net rating gap",
  home_net_rating_l10: "Home net rating L10",
  away_net_rating_l10: "Away net rating L10",
  home_pace_l10: "Home pace L10",
  away_pace_l10: "Away pace L10",
  home_rest_days: "Home rest days",
  away_rest_days: "Away rest days",
  home_b2b: "Home B2B",
  away_b2b: "Away B2B",
  home_distance_traveled: "Home travel",
  away_distance_traveled: "Away travel",
  home_injury_impact: "Home injury impact",
  away_injury_impact: "Away injury impact",
  ref_home_bias: "Ref home bias",
  ref_total_bias: "Ref total bias",
  ref_foul_bias: "Ref foul bias",
};

function formatFeatureLabel(feature: string) {
  return FEATURE_LABELS[feature] ?? feature.replace(/_/g, " ");
}

function formatFeatureValue(value: number) {
  if (Number.isInteger(value)) {
    return value.toString();
  }
  return `${value >= 0 ? "+" : ""}${value.toFixed(Math.abs(value) >= 10 ? 1 : 2)}`;
}

function formatMiles(value: number) {
  return `${Math.round(value).toLocaleString()} mi`;
}

export default function GameDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const gameId = params.id;

  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => getDashboard(),
  });

  const selectedGame =
    dashboardQuery.data?.find((game) => game.game_id === gameId) ??
    (gameId
      ? {
          game_id: gameId,
          home_team: searchParams.get("home") ?? "",
          away_team: searchParams.get("away") ?? "",
          date: searchParams.get("date") ?? "",
          status: "Scheduled",
          edge: null,
          market: undefined,
          market_signals: [],
        }
      : undefined);

  const predictionQuery = useQuery({
    enabled: Boolean(selectedGame?.home_team && selectedGame?.away_team && selectedGame?.date),
    queryKey: ["prediction", gameId, selectedGame?.home_team, selectedGame?.away_team, selectedGame?.date],
    queryFn: () =>
      getPrediction({
        gameId,
        home: selectedGame!.home_team,
        away: selectedGame!.away_team,
        date: selectedGame!.date,
      }),
  });
  const oddsQuery = useQuery({
    enabled: Boolean(gameId),
    queryKey: ["market-odds", gameId],
    queryFn: () => getGameMarketOdds(gameId),
  });

  if (!selectedGame) {
    return (
      <StatusMessage
        title="Game context missing"
        body="This route needs either dashboard context or explicit home, away, and date query params."
      />
    );
  }

  if (predictionQuery.isLoading) {
    return (
      <StatusMessage
        title="Loading matchup model"
        body={`Building the model view for ${selectedGame.away_team} at ${selectedGame.home_team}.`}
      />
    );
  }

  if (predictionQuery.error) {
    return <StatusMessage title="Matchup unavailable" body={(predictionQuery.error as Error).message} />;
  }

  const prediction = predictionQuery.data;
  if (!prediction) {
    return <StatusMessage title="No prediction payload returned" body="The backend did not return a prediction object for this game." />;
  }

  const marketSignals = selectedGame.market_signals ?? prediction.market_signals ?? [];
  const keyDrivers =
    prediction.key_drivers?.length > 0 ? prediction.key_drivers : prediction.projections.top_features ?? [];
  const context = prediction.features_snapshot.context;
  const schedule = prediction.features_snapshot.schedule;
  const winModelSource = prediction.projections.model_source?.win_prob;
  const modelSourceLabel = winModelSource === "trained" ? "Trained XGBoost" : "Fallback model";
  const marketHomeProb = selectedGame.market?.implied_home_prob;
  const projectedSpread = prediction.projections.projected_spread;
  const marketSpread = selectedGame.market?.spread ?? oddsQuery.data?.current_line.home_point ?? null;
  const totalGap =
    selectedGame.market?.total !== null && selectedGame.market?.total !== undefined
      ? prediction.projections.projected_total - selectedGame.market.total
      : null;
  const spreadGap = marketSpread !== null && marketSpread !== undefined ? projectedSpread - marketSpread : null;

  return (
    <div className="flex flex-col gap-5">
      <PageHero
        eyebrow="Matchup Detail"
        title={`${selectedGame.away_team} @ ${selectedGame.home_team}`}
        description="The matchup route is now organized around the actual decision flow: read the thesis, inspect the context, then compare it against the current market path."
        statusLabel={selectedGame.status || "Scheduled"}
      />

      <section className="grid gap-4 xl:grid-cols-4">
        <MetricCard
          label="Home Win"
          value={formatPercent(prediction.projections.home_win_prob, 1)}
          hint={`Model source: ${modelSourceLabel}.`}
          icon={<Gauge className="size-5 text-sky-300" />}
        />
        <MetricCard
          label="Model vs Market"
          value={formatPercent(selectedGame.edge, 1)}
          hint={
            marketHomeProb !== null && marketHomeProb !== undefined
              ? `Market implied ${formatPercent(marketHomeProb, 1)}.`
              : "Waiting for tracked moneyline."
          }
          icon={<Scale className="size-5 text-emerald-300" />}
          tone={(selectedGame.edge ?? 0) > 0 ? "positive" : "warning"}
        />
        <MetricCard
          label="Spread Gap"
          value={formatSignedNumber(spreadGap, 1)}
          hint={
            marketSpread !== null && marketSpread !== undefined
              ? `Market spread ${formatSignedNumber(marketSpread, 1)}.`
              : "No tracked spread yet."
          }
          icon={<Target className="size-5 text-indigo-200" />}
        />
        <MetricCard
          label="Total Gap"
          value={formatSignedNumber(totalGap, 1)}
          hint={
            selectedGame.market?.total !== null && selectedGame.market?.total !== undefined
              ? `Market total ${selectedGame.market.total.toFixed(1)}.`
              : "No tracked total yet."
          }
          icon={<Activity className="size-5 text-sky-300" />}
        />
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.14fr_0.86fr]">
        <ModelDriversPanel
          drivers={keyDrivers}
          formatFeatureLabel={formatFeatureLabel}
          formatFeatureValue={formatFeatureValue}
        />

        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Thesis"
              title="Why the model is here"
              description="Fast summary of directional context, current edge, and team trends attached to the matchup."
            />
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <MetricCard
                label="Signals Attached"
                value={String(marketSignals.length)}
                hint="Recent market events linked to this game."
              />
              <MetricCard
                label="Top Driver"
                value={keyDrivers[0] ? formatFeatureLabel(keyDrivers[0].feature) : "N/A"}
                hint={keyDrivers[0] ? formatPercent(keyDrivers[0].game_impact, 1) : "No driver payload."}
              />
            </div>

            <div className="rounded-[24px] border border-white/8 bg-white/4 p-4">
              <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">Model read</p>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                {selectedGame.home_team} is projected at {formatPercent(prediction.projections.home_win_prob, 1)}
                {" "}to win, with a modeled line of {formatSignedNumber(projectedSpread, 1)} and total of{" "}
                {prediction.projections.projected_total.toFixed(1)}.
              </p>
              <p className="mt-3 text-sm leading-7 text-slate-400">
                {selectedGame.edge !== null && selectedGame.edge !== undefined
                  ? `Against the tracked home moneyline, that translates to a ${formatPercent(selectedGame.edge, 1)} edge.`
                  : "Edge will appear here when market prices are available."}
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-[24px] border border-white/8 bg-white/4 p-4">
                <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                  {selectedGame.home_team} trend tape
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(prediction.trends.home?.length ? prediction.trends.home : ["No tracked trend flags"]).map((flag) => (
                    <Badge key={`${selectedGame.home_team}-${flag}`} variant="accent">
                      {flag}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="rounded-[24px] border border-white/8 bg-white/4 p-4">
                <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                  {selectedGame.away_team} trend tape
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(prediction.trends.away?.length ? prediction.trends.away : ["No tracked trend flags"]).map((flag) => (
                    <Badge key={`${selectedGame.away_team}-${flag}`} variant="default">
                      {flag}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Travel"
              title="Fatigue map"
              description="Rest, travel, and back-to-back strain by team."
            />
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
              <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">{selectedGame.home_team}</p>
              <p className="mt-3 text-2xl font-semibold text-slate-50">{formatMiles(schedule.home_distance_traveled)}</p>
              <p className="mt-2 text-sm text-slate-400">
                {schedule.home_rest_days} rest days · {schedule.home_b2b ? "Back-to-back" : "Normal spot"}
              </p>
            </div>
            <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
              <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">{selectedGame.away_team}</p>
              <p className="mt-3 text-2xl font-semibold text-slate-50">{formatMiles(schedule.away_distance_traveled)}</p>
              <p className="mt-2 text-sm text-slate-400">
                {schedule.away_rest_days} rest days · {schedule.away_b2b ? "Back-to-back" : "Normal spot"}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Officiating"
              title="Crew profile"
              description="Assigned officials and directional bias markers."
            />
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap gap-2">
              {(context.assigned_referees?.length ? context.assigned_referees : ["Ref crew pending"]).map((refName) => (
                <Badge key={refName} variant="warm">
                  {refName}
                </Badge>
              ))}
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <MetricCard label="Home Bias" value={formatPercent(context.ref_home_bias, 1)} hint="Positive leans home." />
              <MetricCard label="Total Bias" value={formatPercent(context.ref_total_bias, 1)} hint="Positive leans over." />
              <MetricCard label="Foul Bias" value={formatPercent(context.ref_foul_bias, 1)} hint="Higher implies more whistles." />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Injuries"
              title="Missing roster value"
              description="Inactive players and injury modifiers from the context pipeline."
            />
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">{selectedGame.home_team}</p>
                <Badge variant={context.home_injury_impact < 0 ? "negative" : "default"}>
                  {formatPercent(context.home_injury_impact, 1)}
                </Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(context.home_inactive_players?.length ? context.home_inactive_players : ["Healthy rotation"]).map((player) => (
                  <Badge key={`${selectedGame.home_team}-${player}`} variant="accent">
                    {player}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">{selectedGame.away_team}</p>
                <Badge variant={context.away_injury_impact < 0 ? "negative" : "default"}>
                  {formatPercent(context.away_injury_impact, 1)}
                </Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(context.away_inactive_players?.length ? context.away_inactive_players : ["Healthy rotation"]).map((player) => (
                  <Badge key={`${selectedGame.away_team}-${player}`} variant="default">
                    {player}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.78fr_1.22fr]">
        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Signals"
              title="Market pressure"
              description="Recent market events already attached to this matchup."
            />
          </CardHeader>
          <CardContent className="space-y-3">
            {marketSignals.length === 0 ? (
              <StatusMessage title="No signal events" body="No recent line-movement or market-pressure records were attached to this matchup." />
            ) : (
              marketSignals.map((signal, index) => (
                <div
                  key={`${signal.type}-${signal.desc}-${index}`}
                  className="rounded-[22px] border border-white/8 bg-white/4 p-4"
                >
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="warm">{signal.type}</Badge>
                      {signal.team ? <Badge variant="default">{signal.team}</Badge> : null}
                    </div>
                    <Waves className="size-4 text-slate-500" />
                  </div>
                  <p className="text-sm leading-7 text-slate-300">{signal.desc}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Odds History"
              title="Stored line path"
              description="Current snapshot and recent stored line entries from `/api/market/odds/:game_id`."
            />
          </CardHeader>
          <CardContent className="space-y-4">
            {oddsQuery.isLoading ? (
              <StatusMessage title="Loading odds history" body="Fetching stored market history for this game." />
            ) : oddsQuery.error ? (
              <StatusMessage title="Odds history unavailable" body={(oddsQuery.error as Error).message} />
            ) : oddsQuery.data ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <MetricCard
                    label="Current Home Price"
                    value={oddsQuery.data.current_line.home_price?.toFixed(2) ?? "N/A"}
                    hint="Latest tracked home decimal."
                  />
                  <MetricCard
                    label="Current Away Price"
                    value={oddsQuery.data.current_line.away_price?.toFixed(2) ?? "N/A"}
                    hint="Latest tracked away decimal."
                  />
                  <MetricCard
                    label="Current Home Point"
                    value={formatSignedNumber(oddsQuery.data.current_line.home_point, 1)}
                    hint="Latest tracked point value."
                  />
                  <MetricCard
                    label="Movement Total"
                    value={formatSignedNumber(oddsQuery.data.movement_total, 1)}
                    hint="Net home-side point movement."
                  />
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Home Price</TableHead>
                      <TableHead>Away Price</TableHead>
                      <TableHead>Home Point</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {oddsQuery.data.history.slice(-10).reverse().map((row, index) => (
                      <TableRow key={`${row.market_type}-${row.timestamp}-${index}`}>
                        <TableCell className="text-slate-400">
                          {row.timestamp ? new Date(row.timestamp).toLocaleString() : "N/A"}
                        </TableCell>
                        <TableCell>{row.market_type ?? "Unknown"}</TableCell>
                        <TableCell>{row.home_price?.toFixed(2) ?? "N/A"}</TableCell>
                        <TableCell>{row.away_price?.toFixed(2) ?? "N/A"}</TableCell>
                        <TableCell>{formatSignedNumber(row.home_point, 1)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            ) : (
              <StatusMessage title="No stored odds history" body="The market history endpoint returned no usable data for this game." />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
