import { t } from "@/shared/i18n/t";
import type { CostPayload, SessionStatus } from "@/shared/realtime/types";
import { CostBadge } from "../CostBadge";

interface SessionStatusBarProps {
  status: SessionStatus;
  stepLabel?: string;
  round?: number;
  cost: CostPayload | null;
}

/** Barre d'état : statut (annoncé poliment), étape, tour, tokens et coût (SPEC 15.2). */
export function SessionStatusBar({ status, stepLabel, round, cost }: SessionStatusBarProps) {
  return (
    <section
      aria-label={t("session.status.label")}
      className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-border bg-card px-3 py-2 text-sm"
    >
      <p role="status" className="font-medium">
        {t(`session.status.${status}`)}
      </p>
      {stepLabel ? <p className="text-muted-foreground">{stepLabel}</p> : null}
      {round !== undefined ? (
        <p className="text-muted-foreground">{t("session.round", { round })}</p>
      ) : null}
      <div className="ml-auto">
        <CostBadge cost={cost} />
      </div>
    </section>
  );
}
