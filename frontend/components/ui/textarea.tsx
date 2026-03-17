import * as React from "react";

import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<"textarea">>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[140px] w-full rounded-[24px] border border-white/10 bg-white/4 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";

export { Textarea };
