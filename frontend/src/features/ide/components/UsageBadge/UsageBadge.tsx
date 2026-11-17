import { t } from "@/shared/i18n/t";
import type { UsageView } from "../viewTypes";

interface UsageBadgeProps {
  usage: UsageView;
}

const NUMBER = new Intl.NumberFormat("fr-FR");

/**
 * Ce que le professeur a consommé : jetons de la séance et du jour face à leurs plafonds. Le mode
 * « Sur demande » (plafond atteint ou choix) s'écrit en toutes lettres : le professeur ne répond
 * plus tout seul, seulement quand on l'appelle.
 */
export function UsageBadge({ usage }: UsageBadgeProps) {
  return (
    <div
      role="group"
      aria-label={t("ide.usage.label")}
      className="flex flex-col gap-1 rounded-xl border border-border bg-card p-3 text-sm"
    >
      <p className="tabular-nums">
        {t("ide.usage.session", {
          used: NUMBER.format(usage.sessionTokens),
          cap: NUMBER.format(usage.sessionCap),
        })}
      </p>
      <p className="tabular-nums">
        {t("ide.usage.day", {
          used: NUMBER.format(usage.dayTokens),
          cap: NUMBER.format(usage.dayCap),
        })}
      </p>
      {usage.onDemand ? (
        <p className="font-medium">
          <span className="rounded border border-border px-1.5">{t("ide.usage.onDemand")}</span>{" "}
          <span className="font-normal text-muted-foreground">{t("ide.usage.onDemandHint")}</span>
        </p>
      ) : null}
    </div>
  );
}
