import { ReactNode } from "react";

import { cn } from "@/lib/utils";

type MetricCardProps = {
  label: string;
  value: string;
  hint?: string;
  icon?: ReactNode;
  tone?: "default" | "positive" | "warning";
};

export function MetricCard({
  label,
  value,
  hint,
  icon,
  tone = "default",
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "panel-surface rounded-[26px] p-5",
        tone === "positive" && "ring-1 ring-emerald-400/24",
        tone === "warning" && "ring-1 ring-amber-300/18",
      )}
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
        {icon}
      </div>
      <p className="text-3xl font-semibold tracking-tight text-slate-50">{value}</p>
      {hint ? <p className="mt-2 text-sm text-slate-400">{hint}</p> : null}
    </div>
  );
}
