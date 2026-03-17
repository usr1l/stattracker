"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ChartColumnBig,
  ChevronRight,
  Crosshair,
  LayoutDashboard,
  Radar,
  Waves,
  Zap,
} from "lucide-react";
import { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const navItems = [
  { href: "/", label: "Board", icon: LayoutDashboard, short: "01" },
  { href: "/live", label: "Live", icon: Activity, short: "02" },
  { href: "/market", label: "Market", icon: Radar, short: "03" },
  { href: "/props", label: "Props", icon: Crosshair, short: "04" },
  { href: "/backtest", label: "Backtest", icon: ChartColumnBig, short: "05" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-[1640px] gap-5 px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
        <aside className="panel-surface noise-mask hidden w-[308px] shrink-0 rounded-[32px] p-5 lg:flex lg:flex-col">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex size-12 items-center justify-center rounded-[18px] border border-sky-300/16 bg-[linear-gradient(135deg,rgba(52,211,255,0.18),rgba(0,255,163,0.12))] shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
                <Waves className="size-5 text-sky-300" />
              </div>
              <div>
                <p className="eyebrow">Stattracker</p>
                <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
                  Market OS
                </h1>
              </div>
            </div>
            <Badge variant="positive">Local</Badge>
          </div>

          <div className="panel-hero mt-6 rounded-[28px] p-5">
            <div className="flex items-center gap-2 text-sm uppercase tracking-[0.2em] text-sky-100/78">
              <Zap className="size-4" />
              Signal mesh
            </div>
            <p className="mt-4 text-2xl font-semibold leading-tight">
              Clean board. Dark surface. One place for model, market, and live edge.
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-300/80">
              Every route stays anchored to the backend APIs, but the scanning flow is simpler and
              less noisy.
            </p>
          </div>

          <nav className="mt-6 flex flex-1 flex-col gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "group flex items-center justify-between rounded-[22px] border px-4 py-3 transition-all",
                    active
                      ? "border-sky-300/18 bg-[linear-gradient(135deg,rgba(52,211,255,0.14),rgba(0,255,163,0.08))] text-white"
                      : "border-transparent text-slate-400 hover:border-white/8 hover:bg-white/4 hover:text-slate-100",
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex size-9 items-center justify-center rounded-[14px] border",
                        active
                          ? "border-sky-300/18 bg-sky-300/12 text-sky-200"
                          : "border-white/8 bg-white/3 text-slate-400",
                      )}
                    >
                      <Icon className="size-4" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="mono text-[11px] tracking-[0.18em] text-slate-500">
                        Route {item.short}
                      </p>
                    </div>
                  </div>
                  <ChevronRight
                    className={cn(
                      "size-4 transition-transform group-hover:translate-x-0.5",
                      active ? "text-sky-200" : "text-slate-600",
                    )}
                  />
                </Link>
              );
            })}
          </nav>

          <div className="grid gap-3">
            <div className="panel-subtle rounded-[24px] p-4">
              <p className="mono text-xs uppercase tracking-[0.18em] text-slate-500">
                Runtime
              </p>
              <div className="mt-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-100">Frontend proxy</p>
                  <p className="text-xs text-slate-400">Next.js hitting Flask under `/api`</p>
                </div>
                <Badge variant="accent">Synced</Badge>
              </div>
            </div>
            <div className="rounded-[24px] border border-white/8 bg-black/18 p-4 text-sm text-slate-400">
              Keep this pass structural. Functionality stays exposed, but the shell is intentionally
              stripped down so future edits are easier.
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col gap-5">
          <header className="panel-surface flex flex-col gap-4 rounded-[28px] p-4 lg:hidden">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="eyebrow">Stattracker</p>
                <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
                  Market OS
                </h1>
              </div>
              <Badge variant="positive">Local</Badge>
            </div>
            <nav className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex shrink-0 items-center gap-2 rounded-full border px-4 py-2 text-sm transition-all",
                      active
                        ? "border-sky-300/18 bg-sky-300/12 text-white"
                        : "border-white/8 bg-white/4 text-slate-400",
                    )}
                  >
                    <Icon className="size-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </header>

          <main className="flex min-w-0 flex-1 flex-col gap-5">{children}</main>
        </div>
      </div>
    </div>
  );
}
