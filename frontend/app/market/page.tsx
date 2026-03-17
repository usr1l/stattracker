"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, CandlestickChart, Radar, Rows3 } from "lucide-react";

import { getDashboard, getFutures, getGameMarketOdds, getMarketSurges } from "@/lib/api";
import { formatSignedNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MetricCard } from "@/components/metric-card";
import { PageHero } from "@/components/page-hero";
import { SectionHeader } from "@/components/section-header";
import { StatusMessage } from "@/components/status-message";

export default function MarketPage() {
  const surgesQuery = useQuery({
    queryKey: ["market-surges"],
    queryFn: () => getMarketSurges(),
  });
  const futuresQuery = useQuery({
    queryKey: ["futures"],
    queryFn: () => getFutures(),
  });
  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => getDashboard(),
  });

  const games = (dashboardQuery.data ?? []).filter((game) => !game.error);
  const [selectedGameId, setSelectedGameId] = useState<string>("");
  const activeGameId = selectedGameId || games[0]?.game_id || "";
  const selectedGame = games.find((game) => game.game_id === activeGameId);
  const oddsQuery = useQuery({
    enabled: Boolean(activeGameId),
    queryKey: ["market-odds", activeGameId],
    queryFn: () => getGameMarketOdds(activeGameId),
  });

  const dominantSignal = useMemo(() => {
    const counts = new Map<string, number>();
    for (const signal of surgesQuery.data ?? []) {
      counts.set(signal.signal_type, (counts.get(signal.signal_type) ?? 0) + 1);
    }
    return [...counts.entries()].sort((left, right) => right[1] - left[1])[0]?.[0] ?? "none";
  }, [surgesQuery.data]);

  return (
    <div className="flex flex-col gap-5">
      <PageHero
        eyebrow="Market Radar"
        title="Movement feed, futures ladder, and line history on one darker rail."
        description="This route now pulls both the market event stream and a selectable game-level odds history so the market endpoints feel like one workflow instead of separate API fragments."
        statusLabel="Surveillance"
      />

      <section className="grid gap-4 xl:grid-cols-4">
        <MetricCard
          label="Signal Events"
          value={surgesQuery.isLoading ? "..." : String(surgesQuery.data?.length ?? 0)}
          hint="Recent market_signals rows."
          icon={<Radar className="size-5 text-sky-300" />}
        />
        <MetricCard
          label="Dominant Signal"
          value={dominantSignal.replaceAll("_", " ")}
          hint="Most common event type in the current feed."
          icon={<Activity className="size-5 text-emerald-300" />}
        />
        <MetricCard
          label="Futures Rows"
          value={futuresQuery.isLoading ? "..." : String(futuresQuery.data?.length ?? 0)}
          hint="Latest futures price rows by market/team."
          icon={<Rows3 className="size-5 text-indigo-200" />}
        />
        <MetricCard
          label="Tracked Matchup"
          value={selectedGame ? `${selectedGame.away_team}/${selectedGame.home_team}` : "N/A"}
          hint="Used for the live odds-history lens below."
          icon={<CandlestickChart className="size-5 text-sky-300" />}
        />
      </section>

      <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Signals"
              title="Recent market events"
              description="Chronological feed of surges, movement, and futures shifts."
            />
          </CardHeader>
          <CardContent className="space-y-3">
            {surgesQuery.isLoading ? (
              <StatusMessage title="Loading market feed" body="Reading surveillance events from the backend." />
            ) : surgesQuery.error ? (
              <StatusMessage title="Market feed unavailable" body={(surgesQuery.error as Error).message} />
            ) : !(surgesQuery.data?.length) ? (
              <StatusMessage title="No market events yet" body="The feed will populate as line movement or futures shifts are detected." />
            ) : (
              surgesQuery.data.map((signal, index) => (
                <div
                  key={`${signal.signal_type}-${signal.timestamp}-${index}`}
                  className="rounded-[24px] border border-white/8 bg-white/4 p-4"
                >
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="warm">{signal.signal_type.replaceAll("_", " ")}</Badge>
                      {signal.team ? <Badge variant="default">{signal.team}</Badge> : null}
                    </div>
                    <span className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                      {new Date(signal.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm leading-7 text-slate-300">{signal.description}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <div className="grid gap-5">
          <Card>
            <CardHeader>
              <SectionHeader
                eyebrow="Odds Lens"
                title="Inspect one game’s line path"
                description="This is the missing piece for the `/api/market/odds/:game_id` endpoint: pick a current game and inspect the stored line snapshots."
              />
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-2">
                <label className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                  Select matchup
                </label>
                <Select value={activeGameId} onChange={(event) => setSelectedGameId(event.target.value)}>
                  {games.length === 0 ? <option value="">No active games</option> : null}
                  {games.map((game) => (
                    <option key={game.game_id} value={game.game_id}>
                      {game.away_team} @ {game.home_team}
                    </option>
                  ))}
                </Select>
              </div>

              {!activeGameId ? (
                <StatusMessage title="No game selected" body="Choose a matchup to inspect the odds history endpoint." />
              ) : oddsQuery.isLoading ? (
                <StatusMessage title="Loading odds history" body="Fetching current line and movement history for the selected game." />
              ) : oddsQuery.error ? (
                <StatusMessage title="Odds history unavailable" body={(oddsQuery.error as Error).message} />
              ) : oddsQuery.data ? (
                <>
                  <div className="grid gap-4 md:grid-cols-3">
                    <MetricCard
                      label="Current Home Price"
                      value={oddsQuery.data.current_line.home_price?.toFixed(2) ?? "N/A"}
                      hint="Latest decimal price."
                    />
                    <MetricCard
                      label="Current Spread"
                      value={formatSignedNumber(oddsQuery.data.current_line.home_point, 1)}
                      hint="Current stored home-side spread."
                    />
                    <MetricCard
                      label="Net Movement"
                      value={formatSignedNumber(oddsQuery.data.movement_total, 1)}
                      hint="Home-side point movement across the stored history."
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
                      {oddsQuery.data.history.slice(-8).reverse().map((row, index) => (
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
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <SectionHeader
                eyebrow="Futures"
                title="Latest futures ladder"
                description="Direct read from `/api/market/futures`."
              />
            </CardHeader>
            <CardContent>
              {futuresQuery.isLoading ? (
                <StatusMessage title="Loading futures" body="Pulling the latest futures prices by team." />
              ) : futuresQuery.error ? (
                <StatusMessage title="Futures unavailable" body={(futuresQuery.error as Error).message} />
              ) : !(futuresQuery.data?.length) ? (
                <StatusMessage title="No futures rows returned" body="Futures prices appear here after the scheduled refresh job writes data." />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Market</TableHead>
                      <TableHead>Team</TableHead>
                      <TableHead>Price</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {futuresQuery.data.map((row, index) => (
                      <TableRow key={`${row.market}-${row.team}-${index}`}>
                        <TableCell className="text-slate-400">{row.market}</TableCell>
                        <TableCell>{row.team}</TableCell>
                        <TableCell>{row.price.toFixed(2)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
