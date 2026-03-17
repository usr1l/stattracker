"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type FeatureDriverChartProps = {
  data: Array<{
    label: string;
    impact: number;
    importance: number;
  }>;
};

export function FeatureDriverChart({ data }: FeatureDriverChartProps) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} barGap={14}>
          <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            width={44}
          />
          <Tooltip
            cursor={{ fill: "rgba(52, 211, 255, 0.08)" }}
            contentStyle={{
              borderRadius: 18,
              border: "1px solid rgba(148, 163, 184, 0.14)",
              backgroundColor: "rgba(6,11,24,0.96)",
              color: "#e2e8f0",
              boxShadow: "0 18px 48px -28px rgba(0,0,0,0.75)",
            }}
            formatter={(value) => {
              const numericValue = Array.isArray(value)
                ? Number(value[0] ?? 0)
                : Number(value ?? 0);
              return `${numericValue.toFixed(1)}%`;
            }}
          />
          <Bar dataKey="impact" fill="#34d3ff" radius={[8, 8, 2, 2]} />
          <Bar dataKey="importance" fill="#00ffa3" radius={[8, 8, 2, 2]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
