"use client";

import { startTransition, useDeferredValue, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Crosshair, Layers3, Search, SlidersHorizontal, Sparkles } from "lucide-react";

import {
  getAdvancedProp,
  getAnalysisAverages,
  getAnalysisCombination,
  getAnalysisProbability,
  getPlayerCareer,
  getPlayerGameLogs,
  getSimplePropProbability,
  getTeams,
  searchPlayers,
} from "@/lib/api";
import type { PlayerGameLog, PropsResult, SimplePropProbability } from "@/lib/types";
import { formatPercent, formatSignedNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MetricCard } from "@/components/metric-card";
import { PageHero } from "@/components/page-hero";
import { SectionHeader } from "@/components/section-header";
import { StatusMessage } from "@/components/status-message";

const advancedStatOptions = ["PTS", "REB", "AST"] as const;
const comboStatOptions = ["PTS", "REB", "AST", "STL", "BLK"] as const;

type SupportedAdvancedStat = (typeof advancedStatOptions)[number];
type SupportedComboStat = (typeof comboStatOptions)[number];

function statValueFromLog(log: PlayerGameLog, stat: SupportedComboStat | SupportedAdvancedStat) {
  const value = log[stat];
  return typeof value === "number" ? value : Number(value ?? 0);
}

function toProbabilityPayload(stat: SupportedComboStat | SupportedAdvancedStat, line: number) {
  const threshold = Math.floor(line) + 1;
  return {
    ast: stat === "AST" ? threshold : undefined,
    reb: stat === "REB" ? threshold : undefined,
    pts: stat === "PTS" ? threshold : undefined,
    stl: stat === "STL" ? threshold : undefined,
    blk: stat === "BLK" ? threshold : undefined,
  };
}

function toComboCriteria(stat: SupportedComboStat, line: number) {
  const threshold = Math.floor(line) + 1;
  return {
    ast: stat === "AST" ? threshold : 0,
    reb: stat === "REB" ? threshold : 0,
    pts: stat === "PTS" ? threshold : 0,
    stl: stat === "STL" ? threshold : 0,
    blk: stat === "BLK" ? threshold : 0,
  };
}

export default function PropsPage() {
  const [search, setSearch] = useState("");
  const [selectedPlayer, setSelectedPlayer] = useState<{ id: number; name: string } | null>(null);
  const [stat, setStat] = useState<SupportedAdvancedStat>("PTS");
  const [line, setLine] = useState("24.5");
  const [opponent, setOpponent] = useState("LAL");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [submitted, setSubmitted] = useState<{
    playerId: number;
    playerName: string;
    stat: SupportedAdvancedStat;
    line: number;
    opponent: string;
    date?: string;
  } | null>(null);

  const [comboSearch, setComboSearch] = useState("");
  const [comboSelectedPlayer, setComboSelectedPlayer] = useState<{ id: number; name: string } | null>(null);
  const [comboStat, setComboStat] = useState<SupportedComboStat>("PTS");
  const [comboLine, setComboLine] = useState("18.5");
  const [comboSubmitted, setComboSubmitted] = useState<{
    primaryId: number;
    primaryName: string;
    primaryStat: SupportedComboStat;
    primaryLine: number;
    secondaryId: number;
    secondaryName: string;
    secondaryStat: SupportedComboStat;
    secondaryLine: number;
  } | null>(null);

  const deferredSearch = useDeferredValue(search);
  const deferredComboSearch = useDeferredValue(comboSearch);

  const playersQuery = useQuery({
    enabled: deferredSearch.trim().length >= 2,
    queryKey: ["players-search", deferredSearch],
    queryFn: () => searchPlayers(deferredSearch),
  });
  const comboPlayersQuery = useQuery({
    enabled: deferredComboSearch.trim().length >= 2,
    queryKey: ["combo-players-search", deferredComboSearch],
    queryFn: () => searchPlayers(deferredComboSearch),
  });
  const teamsQuery = useQuery({
    queryKey: ["teams"],
    queryFn: () => getTeams(),
  });

  const advancedPropQuery = useQuery({
    enabled: submitted !== null,
    queryKey: ["advanced-prop", submitted],
    queryFn: () =>
      getAdvancedProp({
        playerId: submitted!.playerId,
        stat: submitted!.stat,
        line: submitted!.line,
        opponent: submitted!.opponent,
        date: submitted!.date,
      }),
  });
  const simplePropQuery = useQuery({
    enabled: submitted !== null,
    queryKey: ["simple-prop", submitted],
    queryFn: () =>
      getSimplePropProbability({
        playerId: submitted!.playerId,
        stat: submitted!.stat,
        line: submitted!.line,
        numGames: 50,
      }),
  });
  const gameLogsQuery = useQuery({
    enabled: submitted !== null,
    queryKey: ["player-logs", submitted?.playerId, submitted?.stat],
    queryFn: () => getPlayerGameLogs({ playerId: submitted!.playerId, numGames: 12 }),
  });
  const careerQuery = useQuery({
    enabled: submitted !== null,
    queryKey: ["player-career", submitted?.playerId],
    queryFn: () => getPlayerCareer(submitted!.playerId),
  });
  const analysisProbabilityQuery = useQuery({
    enabled: submitted !== null,
    queryKey: ["analysis-probability", submitted],
    queryFn: () =>
      getAnalysisProbability({
        player_id: submitted!.playerId,
        ...toProbabilityPayload(submitted!.stat, submitted!.line),
      }),
  });

  const recentLogs = useMemo(() => gameLogsQuery.data ?? [], [gameLogsQuery.data]);
  const analysisAveragesQuery = useQuery({
    enabled: submitted !== null && recentLogs.length > 0,
    queryKey: ["analysis-averages", submitted?.playerId, recentLogs.length, submitted?.stat],
    queryFn: () =>
      getAnalysisAverages({
        logs: recentLogs.slice(0, 8).map((log) => ({ ...log })),
        cats: ["PTS", "REB", "AST", "STL", "BLK"],
      }),
  });
  const comboProbabilityQuery = useQuery({
    enabled: comboSubmitted !== null,
    queryKey: ["combo-probability", comboSubmitted],
    queryFn: () =>
      getAnalysisCombination({
        player_ids: [comboSubmitted!.primaryId, comboSubmitted!.secondaryId],
        players: [
          toComboCriteria(comboSubmitted!.primaryStat, comboSubmitted!.primaryLine),
          toComboCriteria(comboSubmitted!.secondaryStat, comboSubmitted!.secondaryLine),
        ],
        combine: "all",
      }),
  });

  const result: PropsResult | undefined = advancedPropQuery.data;
  const propProb: SimplePropProbability | undefined = simplePropQuery.data;
  const recentStatAverage = useMemo(() => {
    if (!recentLogs.length) {
      return null;
    }
    const activeStat = submitted?.stat ?? stat;
    const values = recentLogs.slice(0, 8).map((log) => statValueFromLog(log, activeStat));
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }, [recentLogs, stat, submitted?.stat]);
  const careerRows = careerQuery.data ?? [];
  const latestCareerRow = careerRows[careerRows.length - 1];
  const analysisAverages = analysisAveragesQuery.data ?? {};

  return (
    <div className="flex flex-col gap-5">
      <PageHero
        eyebrow="Props Workstation"
        title="Projection, hit-rate, and combo probability on one darker research surface."
        description="The props route now pulls in the analysis endpoints too, so you can move from a single-player projection to a cleaner same-game combo check without leaving the workstation."
        statusLabel="Research"
      />

      <section className="grid gap-4 xl:grid-cols-4">
        <MetricCard
          label="Search"
          value={deferredSearch.trim().length >= 2 ? "Live" : "Idle"}
          hint="Primary player lookup activates after two characters."
          icon={<Search className="size-5 text-sky-300" />}
        />
        <MetricCard
          label="Selected Player"
          value={selectedPlayer?.name ?? "None"}
          hint="Used for both projection and analysis reads."
          icon={<Crosshair className="size-5 text-emerald-300" />}
        />
        <MetricCard
          label="Projection Edge"
          value={result ? formatSignedNumber(result.edge_value, 2) : "Pending"}
          hint="Advanced prop route minus sportsbook line."
          icon={<SlidersHorizontal className="size-5 text-indigo-200" />}
          tone={result && result.edge_value > 0 ? "positive" : "default"}
        />
        <MetricCard
          label="Combo Lab"
          value={comboSubmitted ? "Armed" : "Idle"}
          hint={comboSelectedPlayer ? `Paired with ${comboSelectedPlayer.name}` : "Add a second player to activate."}
          icon={<Layers3 className="size-5 text-sky-300" />}
        />
      </section>

      <div className="grid gap-5 xl:grid-cols-[0.82fr_1.18fr]">
        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Builder"
              title="Configure a prop read"
              description="Search a player, choose the market, and run the model projection and historical probability paths together."
            />
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-2">
              <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                Player search
              </label>
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search player name"
              />
            </div>

            <div className="max-h-60 overflow-auto rounded-[24px] border border-white/8 bg-white/4">
              {deferredSearch.trim().length < 2 ? (
                <div className="p-4 text-sm text-slate-500">Type at least two characters to search.</div>
              ) : playersQuery.isLoading ? (
                <div className="p-4 text-sm text-slate-500">Searching players...</div>
              ) : playersQuery.error ? (
                <div className="p-4 text-sm text-rose-300">{(playersQuery.error as Error).message}</div>
              ) : (
                (playersQuery.data ?? []).slice(0, 10).map((player) => (
                  <button
                    key={player.PERSON_ID}
                    type="button"
                    className="flex w-full items-center justify-between border-b border-white/8 px-4 py-3 text-left text-sm last:border-0 hover:bg-white/4"
                    onClick={() =>
                      setSelectedPlayer({
                        id: Number(player.PERSON_ID),
                        name: player.DISPLAY_FIRST_LAST,
                      })
                    }
                  >
                    <span className="font-medium text-slate-50">{player.DISPLAY_FIRST_LAST}</span>
                    <span className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                      {player.TEAM_ABBREVIATION ?? "NBA"}
                    </span>
                  </button>
                ))
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Stat</label>
                <Select value={stat} onChange={(event) => setStat(event.target.value as SupportedAdvancedStat)}>
                  {advancedStatOptions.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="grid gap-2">
                <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Line</label>
                <Input value={line} onChange={(event) => setLine(event.target.value)} />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Opponent</label>
                <Select value={opponent} onChange={(event) => setOpponent(event.target.value)}>
                  {(teamsQuery.data ?? []).map((team) => (
                    <option key={team.id} value={team.abbreviation}>
                      {team.abbreviation} · {team.full_name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="grid gap-2">
                <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Game date</label>
                <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {selectedPlayer ? (
                <Badge variant="accent">{selectedPlayer.name}</Badge>
              ) : (
                <Badge variant="default">Select a player from search results</Badge>
              )}
              <Badge variant="warm">Opponent {opponent}</Badge>
              <Badge variant="default">{stat} market</Badge>
            </div>

            <Button
              type="button"
              disabled={!selectedPlayer}
              onClick={() => {
                if (!selectedPlayer) {
                  return;
                }
                startTransition(() => {
                  setSubmitted({
                    playerId: selectedPlayer.id,
                    playerName: selectedPlayer.name,
                    stat,
                    line: Number(line),
                    opponent,
                    date,
                  });
                });
              }}
            >
              <Crosshair className="size-4" />
              Run prop workstation
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Projection"
              title="Advanced model output"
              description="XGBoost-style projection, simpler hit rate, and analysis probability now sit together instead of being split across separate tooling."
            />
          </CardHeader>
          <CardContent className="space-y-4">
            {!submitted ? (
              <StatusMessage title="Awaiting a prop query" body="Select a player and submit the form to compute the prop read." />
            ) : advancedPropQuery.isLoading || simplePropQuery.isLoading || analysisProbabilityQuery.isLoading ? (
              <StatusMessage title="Running prop models" body="Pulling projection, hit rate, and direct probability analysis from the backend." />
            ) : advancedPropQuery.error ? (
              <StatusMessage title="Advanced prop failed" body={(advancedPropQuery.error as Error).message} />
            ) : simplePropQuery.error ? (
              <StatusMessage title="Historical prop read failed" body={(simplePropQuery.error as Error).message} />
            ) : analysisProbabilityQuery.error ? (
              <StatusMessage title="Analysis read failed" body={(analysisProbabilityQuery.error as Error).message} />
            ) : result ? (
              <>
                <div className="grid gap-4 md:grid-cols-5">
                  <MetricCard label="Projected" value={result.projected_line.toFixed(2)} hint="Model estimate." />
                  <MetricCard label="Sportsbook" value={result.sportsbook_line.toFixed(1)} hint="Input line." />
                  <MetricCard
                    label="Model Edge"
                    value={formatSignedNumber(result.edge_value, 2)}
                    hint={result.recommended_bet}
                    tone={result.edge_value > 0 ? "positive" : "warning"}
                  />
                  <MetricCard
                    label="Simple Hit Rate"
                    value={propProb ? formatPercent(propProb.over_pct, 1) : "N/A"}
                    hint={propProb ? `${propProb.sample_size} game sample` : "Historical probability"}
                  />
                  <MetricCard
                    label="Analysis Hit Rate"
                    value={analysisProbabilityQuery.data?.percentage ?? "N/A"}
                    hint={analysisProbabilityQuery.data?.criteria || "Direct analysis engine"}
                  />
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <MetricCard
                    label="Base"
                    value={result.modifiers_applied.base_projection.toFixed(2)}
                    hint="Before matchup multipliers."
                  />
                  <MetricCard
                    label="Defense Mod"
                    value={result.modifiers_applied.opponent_defense_mod.toFixed(3)}
                    hint="Opponent defense-vs-position factor."
                  />
                  <MetricCard
                    label="Pace Mod"
                    value={result.modifiers_applied.pace_mod.toFixed(3)}
                    hint="Tempo adjustment."
                  />
                </div>
              </>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.18fr_0.82fr]">
        <Card>
          <CardHeader>
            <SectionHeader
              eyebrow="Recent Form"
              title="Last game logs"
              description="Pulled from `/api/stats/player/:id/gamelogs` so form and matchup context stay adjacent to the prop decision."
            />
          </CardHeader>
          <CardContent>
            {!submitted ? (
              <StatusMessage title="No player selected" body="Run a prop query to inspect the player’s recent logs." />
            ) : gameLogsQuery.isLoading ? (
              <StatusMessage title="Loading logs" body="Fetching recent player game logs." />
            ) : gameLogsQuery.error ? (
              <StatusMessage title="Game logs unavailable" body={(gameLogsQuery.error as Error).message} />
            ) : !recentLogs.length ? (
              <StatusMessage title="No logs returned" body="The stats endpoint did not return any recent games." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Matchup</TableHead>
                    <TableHead>{submitted?.stat ?? stat}</TableHead>
                    <TableHead>MIN</TableHead>
                    <TableHead>WL</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentLogs.slice(0, 8).map((log, index) => (
                    <TableRow key={`${log.GAME_ID ?? log.GAME_DATE}-${index}`}>
                      <TableCell className="text-slate-400">{String(log.GAME_DATE ?? "N/A")}</TableCell>
                      <TableCell>{String(log.MATCHUP ?? "N/A")}</TableCell>
                      <TableCell>{statValueFromLog(log, submitted?.stat ?? stat)}</TableCell>
                      <TableCell>{String(log.MIN ?? "N/A")}</TableCell>
                      <TableCell>{String(log.WL ?? "N/A")}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-5">
          <Card>
            <CardHeader>
              <SectionHeader
                eyebrow="Context"
                title="Quick read"
                description="Career, recent average, and server-side averages from the analysis engine."
              />
            </CardHeader>
            <CardContent className="space-y-4">
              <MetricCard
                label="Recent Avg"
                value={recentStatAverage !== null ? recentStatAverage.toFixed(1) : "N/A"}
                hint={`Last 8 games in ${submitted?.stat ?? stat}.`}
              />
              <MetricCard
                label="Threshold"
                value={propProb ? String(propProb.line_threshold_integer) : "N/A"}
                hint="Rounded historical hit threshold."
              />
              <MetricCard
                label="Career Rows"
                value={submitted ? String(careerRows.length) : "N/A"}
                hint="Rows returned from `/api/stats/player/:id/career`."
              />
              <div className="grid gap-3 md:grid-cols-3">
                <MetricCard
                  label="PTS Avg"
                  value={typeof analysisAverages.PTS === "number" ? analysisAverages.PTS.toFixed(1) : "N/A"}
                  hint="Server-side average."
                />
                <MetricCard
                  label="REB Avg"
                  value={typeof analysisAverages.REB === "number" ? analysisAverages.REB.toFixed(1) : "N/A"}
                  hint="Server-side average."
                />
                <MetricCard
                  label="AST Avg"
                  value={typeof analysisAverages.AST === "number" ? analysisAverages.AST.toFixed(1) : "N/A"}
                  hint="Server-side average."
                />
              </div>
              {latestCareerRow ? (
                <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                  <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                    Latest career row
                  </p>
                  <p className="mt-3 text-sm text-slate-300">
                    GP {String(latestCareerRow.GP ?? "N/A")} · PTS {String(latestCareerRow.PTS ?? "N/A")} · REB{" "}
                    {String(latestCareerRow.REB ?? "N/A")} · AST {String(latestCareerRow.AST ?? "N/A")}
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <SectionHeader
                eyebrow="Combo Lab"
                title="Same-game combo probability"
                description="Uses the analysis combination endpoint so the props route can check multi-leg historical hit rates too."
              />
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">Primary leg</p>
                <p className="mt-3 text-sm text-slate-300">
                  {submitted
                    ? `${submitted.playerName} ${Math.floor(submitted.line) + 1}+ ${submitted.stat}`
                    : "Run a primary prop query first."}
                </p>
              </div>

              <div className="grid gap-2">
                <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                  Second player search
                </label>
                <Input
                  value={comboSearch}
                  onChange={(event) => setComboSearch(event.target.value)}
                  placeholder="Search teammate or opponent"
                />
              </div>

              <div className="max-h-44 overflow-auto rounded-[24px] border border-white/8 bg-white/4">
                {deferredComboSearch.trim().length < 2 ? (
                  <div className="p-4 text-sm text-slate-500">Type at least two characters to search.</div>
                ) : comboPlayersQuery.isLoading ? (
                  <div className="p-4 text-sm text-slate-500">Searching players...</div>
                ) : comboPlayersQuery.error ? (
                  <div className="p-4 text-sm text-rose-300">{(comboPlayersQuery.error as Error).message}</div>
                ) : (
                  (comboPlayersQuery.data ?? [])
                    .filter((player) => Number(player.PERSON_ID) !== selectedPlayer?.id)
                    .slice(0, 8)
                    .map((player) => (
                      <button
                        key={`combo-${player.PERSON_ID}`}
                        type="button"
                        className="flex w-full items-center justify-between border-b border-white/8 px-4 py-3 text-left text-sm last:border-0 hover:bg-white/4"
                        onClick={() =>
                          setComboSelectedPlayer({
                            id: Number(player.PERSON_ID),
                            name: player.DISPLAY_FIRST_LAST,
                          })
                        }
                      >
                        <span className="font-medium text-slate-50">{player.DISPLAY_FIRST_LAST}</span>
                        <span className="mono text-xs uppercase tracking-[0.16em] text-slate-500">
                          {player.TEAM_ABBREVIATION ?? "NBA"}
                        </span>
                      </button>
                    ))
                )}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Second leg stat</label>
                  <Select value={comboStat} onChange={(event) => setComboStat(event.target.value as SupportedComboStat)}>
                    {comboStatOptions.map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="grid gap-2">
                  <label className="mono text-xs uppercase tracking-[0.16em] text-slate-500">Second leg line</label>
                  <Input value={comboLine} onChange={(event) => setComboLine(event.target.value)} />
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {comboSelectedPlayer ? (
                  <Badge variant="accent">{comboSelectedPlayer.name}</Badge>
                ) : (
                  <Badge variant="default">Select a second player</Badge>
                )}
                <Badge variant="warm">{Math.floor(Number(comboLine || 0)) + 1}+ {comboStat}</Badge>
              </div>

              <Button
                type="button"
                disabled={!submitted || !comboSelectedPlayer}
                onClick={() => {
                  if (!submitted || !comboSelectedPlayer) {
                    return;
                  }
                  startTransition(() => {
                    setComboSubmitted({
                      primaryId: submitted.playerId,
                      primaryName: submitted.playerName,
                      primaryStat: submitted.stat,
                      primaryLine: submitted.line,
                      secondaryId: comboSelectedPlayer.id,
                      secondaryName: comboSelectedPlayer.name,
                      secondaryStat: comboStat,
                      secondaryLine: Number(comboLine),
                    });
                  });
                }}
              >
                <Sparkles className="size-4" />
                Run combo check
              </Button>

              {!comboSubmitted ? (
                <StatusMessage title="Combo lab idle" body="Add a second player to estimate a same-game historical hit rate." />
              ) : comboProbabilityQuery.isLoading ? (
                <StatusMessage title="Running combo analysis" body="Comparing overlapping game logs for both legs." />
              ) : comboProbabilityQuery.error ? (
                <StatusMessage title="Combo analysis failed" body={(comboProbabilityQuery.error as Error).message} />
              ) : comboProbabilityQuery.data ? (
                <div className="rounded-[22px] border border-emerald-300/16 bg-emerald-300/6 p-4">
                  <p className="mono text-xs uppercase tracking-[0.18em] text-emerald-200/80">
                    Combo result
                  </p>
                  <p className="mt-3 text-sm leading-7 text-slate-200">
                    {comboSubmitted.primaryName} {Math.floor(comboSubmitted.primaryLine) + 1}+{" "}
                    {comboSubmitted.primaryStat} + {comboSubmitted.secondaryName}{" "}
                    {Math.floor(comboSubmitted.secondaryLine) + 1}+ {comboSubmitted.secondaryStat}
                  </p>
                  <p className="mt-3 text-sm text-emerald-100">
                    {comboProbabilityQuery.data.result}
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
