"use client";

import { useMutation } from "@tanstack/react-query";
import { ChartColumnBig, Database, FlaskConical, Wallet } from "lucide-react";
import { useMemo, useState } from "react";

import { runBacktest } from "@/lib/api";
import { SAMPLE_BACKTEST_GAMES } from "@/lib/sample-backtest";
import type { BacktestGameInput, BacktestResult } from "@/lib/types";
import { formatMoney, formatPercent, formatSignedNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { BankrollChart } from "@/components/charts/bankroll-chart";
import { EdgeReturnScatter } from "@/components/charts/edge-return-scatter";
import { MetricCard } from "@/components/metric-card";
import { PageHero } from "@/components/page-hero";
import { SectionHeader } from "@/components/section-header";
import { StatusMessage } from "@/components/status-message";

function formatClv(value: number, unit: string) {
  if (unit === "points") {
    return `${formatSignedNumber(value, 2)} pts`;
  }
  return `${formatSignedNumber(value * 100, 2)} pp`;
}

export default function BacktestPage() {
  const [mode, setMode] = useState<"manual" | "historical">("historical");
  const [startingBankroll, setStartingBankroll] = useState("10000");
  const [kellyFraction, setKellyFraction] = useState("0.25");
  const [seasons, setSeasons] = useState("2025-26,2024-25,2023-24");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [limit, setLimit] = useState("250");
  const [gamesText, setGamesText] = useState(JSON.stringify(SAMPLE_BACKTEST_GAMES, null, 2));
  const [parseError, setParseError] = useState<string | null>(null);

  const backtestMutation = useMutation<
    BacktestResult,
    Error,
    {
      games?: BacktestGameInput[];
      starting_bankroll: number;
      kelly_fraction: number;
      seasons?: string[];
      date_from?: string;
      date_to?: string;
      limit?: number;
    }
  >({
    mutationFn: runBacktest,
  });

  const backtestResult = backtestMutation.data;
  const mutationError = backtestMutation.error?.message ?? "Backtest request failed.";
  const recommendedSweep = backtestResult?.fraction_sweep.find(
    (row) => row.kelly_fraction === backtestResult.recommended_kelly_fraction,
  );
  const gamesCount = useMemo(() => {
    try {
      return JSON.parse(gamesText).length;
    } catch {
      return 0;
    }
  }, [gamesText]);

  return (
    <div className="flex flex-col gap-5">
      <PageHero
        eyebrow="Backtest Desk"
        title="Run either a pasted simulation or a database-backed historical replay."
        description="This version makes the route less clumsy: you can switch between manual payload mode and the imported `historical_odds` path without editing JSON unless you want to."
        statusLabel="Analytics"
      />

      <section className="grid gap-4 xl:grid-cols-4">
        <MetricCard
          label="Mode"
          value={mode === "historical" ? "Historical DB" : "Manual"}
          hint="Switches between DB-backed and pasted payload backtests."
          icon={<Database className="size-5 text-sky-300" />}
        />
        <MetricCard
          label="Sample Rows"
          value={mode === "manual" ? String(gamesCount) : "DB"}
          hint="Editable payload rows in manual mode."
          icon={<FlaskConical className="size-5 text-indigo-200" />}
        />
        <MetricCard
          label="Kelly Fraction"
          value={formatPercent(Number(kellyFraction), 0)}
          hint="Fractional Kelly applied to qualifying edges."
          icon={<Wallet className="size-5 text-emerald-300" />}
        />
        <MetricCard
          label="Recommended Kelly"
          value={backtestResult ? formatPercent(backtestResult.recommended_kelly_fraction, 0) : "Pending"}
          hint={recommendedSweep ? `Sweep score ${recommendedSweep.score.toFixed(1)}` : "Appears after a run."}
          icon={<ChartColumnBig className="size-5 text-sky-300" />}
        />
      </section>

      <div className="grid gap-5 xl:grid-cols-[0.86fr_1.14fr]">
        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Configuration"
              title="Backtest inputs"
              description="Cleaner split between database replay mode and manual simulation mode."
            />
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-2">
              <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Mode</label>
              <Select value={mode} onChange={(event) => setMode(event.target.value as "manual" | "historical")}>
                <option value="historical">Historical DB</option>
                <option value="manual">Manual payload</option>
              </Select>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                  Starting bankroll
                </label>
                <Input
                  type="number"
                  min="1000"
                  step="100"
                  value={startingBankroll}
                  onChange={(event) => setStartingBankroll(event.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                  Kelly fraction
                </label>
                <Input
                  type="number"
                  min="0.05"
                  max="1"
                  step="0.05"
                  value={kellyFraction}
                  onChange={(event) => setKellyFraction(event.target.value)}
                />
              </div>
            </div>

            {mode === "historical" ? (
              <>
                <div className="grid gap-2">
                  <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                    Seasons
                  </label>
                  <Input
                    value={seasons}
                    onChange={(event) => setSeasons(event.target.value)}
                    placeholder="2025-26,2024-25,2023-24"
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="grid gap-2">
                    <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Date from</label>
                    <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                  </div>
                  <div className="grid gap-2">
                    <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Date to</label>
                    <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
                  </div>
                  <div className="grid gap-2">
                    <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Limit</label>
                    <Input value={limit} onChange={(event) => setLimit(event.target.value)} />
                  </div>
                </div>
                <div className="rounded-[22px] border border-white/8 bg-white/4 p-4 text-sm text-slate-400">
                  Historical mode sends no `games` payload and lets the backend join
                  `team_game_logs` with imported `historical_odds`.
                </div>
              </>
            ) : (
              <>
                <div className="grid gap-2">
                  <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                    Games payload
                  </label>
                  <Textarea
                    value={gamesText}
                    onChange={(event) => setGamesText(event.target.value)}
                    className="min-h-[420px] font-mono text-xs leading-6"
                  />
                </div>
                {parseError ? <p className="text-sm text-rose-300">{parseError}</p> : null}
              </>
            )}

            <Button
              type="button"
              onClick={() => {
                setParseError(null);
                try {
                  const payload =
                    mode === "manual"
                      ? {
                          games: JSON.parse(gamesText),
                          starting_bankroll: Number(startingBankroll),
                          kelly_fraction: Number(kellyFraction),
                        }
                      : {
                          starting_bankroll: Number(startingBankroll),
                          kelly_fraction: Number(kellyFraction),
                          seasons: seasons
                            .split(",")
                            .map((value) => value.trim())
                            .filter(Boolean),
                          date_from: dateFrom || undefined,
                          date_to: dateTo || undefined,
                          limit: limit ? Number(limit) : undefined,
                        };
                  backtestMutation.mutate(payload);
                } catch (error) {
                  setParseError((error as Error).message);
                }
              }}
            >
              Run backtest
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Output"
              title="Performance readout"
              description="Same analytics as before, but organized around the actual questions: profitability, calibration, and where edge quality starts paying."
            />
          </CardHeader>
          <CardContent className="space-y-5">
            {!backtestResult && !backtestMutation.isPending ? (
              <StatusMessage title="No backtest run yet" body="Submit the form to render bankroll, CLV, and confidence-tier analytics." />
            ) : backtestMutation.isPending ? (
              <StatusMessage title="Running backtest" body="The backend is grading the selected historical sample." />
            ) : backtestMutation.error ? (
              <StatusMessage title="Backtest failed" body={mutationError} />
            ) : backtestResult ? (
              <>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard
                    label="ROI"
                    value={formatPercent(backtestResult.roi_percent / 100, 1)}
                    hint={`${backtestResult.total_bets} bets across ${backtestResult.games_processed} games.`}
                    tone="positive"
                  />
                  <MetricCard
                    label="Win Rate"
                    value={formatPercent(backtestResult.win_rate, 1)}
                    hint={`${backtestResult.wins} wins / ${backtestResult.losses} losses / ${backtestResult.pushes ?? 0} pushes`}
                  />
                  <MetricCard
                    label="Avg CLV"
                    value={formatClv(backtestResult.average_clv, backtestResult.clv_unit)}
                    hint="Closing line value on graded bets."
                  />
                  <MetricCard
                    label="Drawdown"
                    value={formatMoney(backtestResult.max_drawdown)}
                    hint={backtestResult.data_source === "historical_odds_db" ? "Historical DB mode." : "Manual payload mode."}
                    tone="warning"
                  />
                </div>

                <div className="rounded-[26px] border border-white/8 bg-white/4 p-5">
                  <div className="mb-4">
                    <p className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                      Bankroll curve
                    </p>
                    <p className="mt-1 text-lg font-semibold text-slate-50">
                      {formatMoney(backtestResult.starting_bankroll)} to{" "}
                      {formatMoney(backtestResult.ending_bankroll)}
                    </p>
                  </div>
                  <BankrollChart data={backtestResult.bankroll_history} />
                </div>

                <div className="rounded-[26px] border border-white/8 bg-white/4 p-5">
                  <div className="mb-4">
                    <p className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Edge vs return</p>
                    <p className="mt-1 text-lg font-semibold text-slate-50">
                      Higher edges should convert into better realized returns
                    </p>
                  </div>
                  {backtestResult.bet_history.length ? (
                    <EdgeReturnScatter data={backtestResult.bet_history} />
                  ) : (
                    <StatusMessage title="No bet history returned" body="The backtest did not place any qualifying bets, so there is no scatter plot to render." />
                  )}
                </div>

                <div className="grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
                  <div className="rounded-[26px] border border-white/8 bg-white/4 p-5">
                    <div className="mb-4">
                      <p className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                        Kelly sweep
                      </p>
                      <p className="mt-1 text-lg font-semibold text-slate-50">
                        Fractional Kelly comparison
                      </p>
                    </div>
                    <div className="grid gap-3">
                      {backtestResult.fraction_sweep.map((row) => (
                        <div
                          key={row.kelly_fraction}
                          className="rounded-[20px] border border-white/8 bg-black/18 p-4"
                        >
                          <div className="mb-2 flex items-center justify-between gap-3">
                            <p className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                              {formatPercent(row.kelly_fraction, 0)} Kelly
                            </p>
                            {row.kelly_fraction === backtestResult.recommended_kelly_fraction ? (
                              <Badge variant="accent">Recommended</Badge>
                            ) : null}
                          </div>
                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <p className="text-slate-500">Ending roll</p>
                              <p className="mt-1 font-semibold text-slate-50">{formatMoney(row.ending_bankroll)}</p>
                            </div>
                            <div>
                              <p className="text-slate-500">ROI / CLV</p>
                              <p className="mt-1 font-semibold text-slate-50">
                                {formatPercent(row.roi_percent / 100, 1)} / {formatClv(row.average_clv, backtestResult.clv_unit)}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="grid gap-5">
                    <div className="rounded-[26px] border border-white/8 bg-white/4 p-5">
                      <div className="mb-4">
                        <p className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                          Confidence calibration
                        </p>
                        <p className="mt-1 text-lg font-semibold text-slate-50">
                          Win rate by confidence bucket
                        </p>
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Bucket</TableHead>
                            <TableHead>Bets</TableHead>
                            <TableHead>Win Rate</TableHead>
                            <TableHead>Avg Edge</TableHead>
                            <TableHead>Gap</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {backtestResult.confidence_buckets.map((bucket) => (
                            <TableRow key={bucket.label}>
                              <TableCell>{bucket.label}</TableCell>
                              <TableCell>{bucket.bets}</TableCell>
                              <TableCell>{formatPercent(bucket.win_rate, 1)}</TableCell>
                              <TableCell>{formatPercent(bucket.average_edge, 1)}</TableCell>
                              <TableCell>{`${formatSignedNumber(bucket.calibration_gap * 100, 1)}%`}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>

                    <div className="rounded-[26px] border border-white/8 bg-white/4 p-5">
                      <div className="mb-4">
                        <p className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                          Edge tiers
                        </p>
                        <p className="mt-1 text-lg font-semibold text-slate-50">
                          ROI by confidence tier
                        </p>
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Tier</TableHead>
                            <TableHead>Bets</TableHead>
                            <TableHead>Win Rate</TableHead>
                            <TableHead>ROI</TableHead>
                            <TableHead>CLV</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {backtestResult.confidence_tiers.map((tier) => (
                            <TableRow key={tier.label}>
                              <TableCell>{tier.label}</TableCell>
                              <TableCell>{tier.bets}</TableCell>
                              <TableCell>{formatPercent(tier.win_rate, 1)}</TableCell>
                              <TableCell>{formatSignedNumber(tier.roi_percent, 1)}%</TableCell>
                              <TableCell>{formatClv(tier.average_clv, backtestResult.clv_unit)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </div>
              </>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
