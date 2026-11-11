import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { BraveUsageView } from "../viewTypes";

interface BraveUsageMeterProps {
  usage: BraveUsageView;
}

const MONTH = /^(\d{4})-(0[1-9]|1[0-2])$/;

/** « 2026-11 » devient « novembre 2026 » (UTC, comme le mois civil du compteur) ; sinon tel quel. */
function monthLabel(month: string): string {
  const match = MONTH.exec(month);
  if (!match) return month;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1));
  return new Intl.DateTimeFormat("fr-FR", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

/** Consommation Brave du mois : texte, jauge, et avertissement une fois le plafond atteint. */
export function BraveUsageMeter({ usage }: BraveUsageMeterProps) {
  if (!usage.hasKey) {
    return <p className="text-sm text-muted-foreground">{t("settings.search.usage.inactive")}</p>;
  }
  const full = usage.used >= usage.cap;
  const ratio = usage.cap > 0 ? Math.min(usage.used / usage.cap, 1) : 1;
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-sm">
        {t("settings.search.usage.count", {
          used: usage.used,
          cap: usage.cap,
          month: monthLabel(usage.month),
        })}
      </p>
      <div
        role="progressbar"
        aria-label={t("settings.search.usage.label")}
        aria-valuemin={0}
        aria-valuemax={usage.cap}
        aria-valuenow={usage.used}
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className={cn("h-full rounded-full", full ? "bg-destructive" : "bg-primary")}
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
      {full && <p className="text-sm text-destructive">{t("settings.search.usage.capReached")}</p>}
    </div>
  );
}
