import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { StatusView } from "../viewTypes";

interface StatusBadgeProps {
  status: StatusView;
  className?: string;
}

/** The « arrivés » (offer) and « perdus » (refusal, no answer, withdrawn) statuses stand apart from
 * the normal thread. */
const TONE: Record<StatusView, string> = {
  to_apply: "border-border bg-muted text-foreground",
  applied: "border-primary/40 bg-primary/10 text-foreground",
  followed_up: "border-primary/40 bg-primary/10 text-foreground",
  interview: "border-primary bg-primary text-primary-foreground",
  offer: "border-primary bg-primary text-primary-foreground",
  rejected: "border-destructive/50 bg-destructive/10 text-destructive",
  no_answer: "border-border bg-background text-muted-foreground",
  withdrawn: "border-border bg-background text-muted-foreground",
};

/** An application's status, always written in words (the tint is only reinforcement). */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex items-center rounded-md border px-1.5 py-0.5 text-xs font-medium whitespace-nowrap",
        TONE[status],
        className,
      )}
    >
      {t(`applications.status.${status}`)}
    </span>
  );
}
