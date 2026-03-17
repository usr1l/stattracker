"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ValueType } from "recharts/types/component/DefaultTooltipContent";

type BankrollChartProps = {
  data: Array<{
    index: number;
    label: string;
    bankroll: number;
  }>;
};

const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function formatTooltipValue(value: ValueType | undefined) {
  if (Array.isArray(value)) {
    return usdFormatter.format(Number(value[0] ?? 0));
  }
  return usdFormatter.format(Number(value ?? 0));
}

export function BankrollChart({ data }: BankrollChartProps) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            minTickGap={28}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            width={66}
          />
          <Tooltip
            formatter={formatTooltipValue}
            contentStyle={{
              borderRadius: 18,
              border: "1px solid rgba(148, 163, 184, 0.14)",
              backgroundColor: "rgba(6,11,24,0.96)",
              color: "#e2e8f0",
              boxShadow: "0 18px 48px -28px rgba(0,0,0,0.75)",
            }}
          />
          <Line
            dataKey="bankroll"
            type="monotone"
            stroke="#34d3ff"
            strokeWidth={3}
            dot={{ r: 0 }}
            activeDot={{ r: 4, fill: "#00ffa3", stroke: "#08101d", strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
