"use client";

import type { PredictionFeatureDriver } from "@/lib/types";
import { formatPercent } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { FeatureDriverChart } from "@/components/charts/feature-driver-chart";
import { SectionHeader } from "@/components/section-header";
import { StatusMessage } from "@/components/status-message";

type ModelDriversPanelProps = {
  drivers: PredictionFeatureDriver[];
  formatFeatureLabel: (feature: string) => string;
  formatFeatureValue: (value: number) => string;
};

export function ModelDriversPanel({
  drivers,
  formatFeatureLabel,
  formatFeatureValue,
}: ModelDriversPanelProps) {
  const chartData = drivers.map((driver) => ({
    label: formatFeatureLabel(driver.feature),
    impact: Number((driver.game_impact * 100).toFixed(1)),
    importance: Number((driver.importance * 100).toFixed(1)),
  }));

  return (
    <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
      <Card>
        <CardHeader>
          <SectionHeader
            eyebrow="Model Drivers"
            title="Top feature importances"
            description="Impact bars show which inputs were most active for this game; importance bars show how strongly the trained win model weights them overall."
          />
        </CardHeader>
        <CardContent>
          <FeatureDriverChart data={chartData} />
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {drivers.length === 0 ? (
          <StatusMessage
            title="No feature drivers returned"
            body="The backend did not attach feature importance data to this prediction."
          />
        ) : (
          drivers.map((driver) => (
            <Card key={driver.feature}>
              <CardContent className="flex flex-col gap-3 p-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                    {formatFeatureLabel(driver.feature)}
                  </p>
                  <div className="flex items-center gap-2">
                    {driver.impact ? <Badge variant="accent">{driver.impact}</Badge> : null}
                    <Badge variant="warm">{formatPercent(driver.importance, 0)} importance</Badge>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-slate-500">Game Impact</p>
                    <p className="mt-1 text-lg font-semibold text-slate-50">
                      {formatPercent(driver.game_impact, 1)}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Current Value</p>
                    <p className="mt-1 text-lg font-semibold text-slate-50">
                      {formatFeatureValue(driver.value)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
