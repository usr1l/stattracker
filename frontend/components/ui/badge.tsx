import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium tracking-[0.16em] uppercase",
  {
    variants: {
      variant: {
        default: "border-white/10 bg-white/4 text-slate-300",
        positive: "border-emerald-400/22 bg-emerald-400/10 text-emerald-300",
        negative: "border-rose-400/20 bg-rose-400/10 text-rose-300",
        accent: "border-sky-400/20 bg-sky-400/10 text-sky-300",
        warm: "border-indigo-300/18 bg-indigo-300/10 text-indigo-200",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
