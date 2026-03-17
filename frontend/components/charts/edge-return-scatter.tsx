"use client";

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type EdgeReturnScatterProps = {
  data: Array<{
    matchup: string;
    side: string;
    edge_pct: number;
    return_pct: number;
    date: string;
  }>;
};

export function EdgeReturnScatter({ data }: EdgeReturnScatterProps) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 18, right: 12, bottom: 18, left: 4 }}>
          <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" />
          <XAxis
            type="number"
            dataKey="edge_pct"
            name="Edge"
            unit="%"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey="return_pct"
            name="Return"
            unit="%"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            width={52}
          />
          <Tooltip
            cursor={{ strokeDasharray: "4 4" }}
            contentStyle={{
              borderRadius: 18,
              border: "1px solid rgba(148, 163, 184, 0.14)",
              backgroundColor: "rgba(6,11,24,0.96)",
              color: "#e2e8f0",
              boxShadow: "0 18px 48px -28px rgba(0,0,0,0.75)",
            }}
            formatter={(value) => `${Number(value ?? 0).toFixed(1)}%`}
            labelFormatter={(_, payload) => {
              const point = payload?.[0]?.payload as EdgeReturnScatterProps["data"][number] | undefined;
              if (!point) {
                return "";
              }
              return `${point.matchup} • ${point.side.toUpperCase()} • ${point.date}`;
            }}
          />
          <Scatter data={data} fill="#34d3ff" fillOpacity={0.85} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
