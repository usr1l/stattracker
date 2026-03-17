import { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

type PageHeroProps = {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
  statusLabel?: string;
};

export function PageHero({
  eyebrow,
  title,
  description,
  actions,
  statusLabel = "Live",
}: PageHeroProps) {
  return (
    <Card className="panel-hero overflow-hidden border-none">
      <CardContent className="p-7 md:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex items-center gap-3">
              <p className="mono text-xs uppercase tracking-[0.22em] text-sky-100/70">{eyebrow}</p>
              <Badge variant="warm">{statusLabel}</Badge>
            </div>
            <h2 className="mt-4 text-4xl font-semibold tracking-tight text-white md:text-5xl">
              {title}
            </h2>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300/80">{description}</p>
          </div>
          {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
        </div>
      </CardContent>
    </Card>
  );
}
