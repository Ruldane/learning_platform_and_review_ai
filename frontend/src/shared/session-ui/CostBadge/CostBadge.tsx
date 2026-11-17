import { t } from "@/shared/i18n/t";
import type { CostPayload } from "@/shared/realtime/types";

interface CostBadgeProps {
  cost: CostPayload | null;
}

const integer = new Intl.NumberFormat("fr-FR");

/**
 * « ≈ 0,04 » : deux décimales, trois sous le centime ; « < 0,001 » sous le millième, sans « ≈ »
 * devant (« ≈ < » ne se lit pas). Un coût non nul ne s'affiche jamais « 0,00 » ni « 0,000 ».
 */
function formatCost(usd: number): string {
  if (usd > 0 && usd < 0.001) return "< 0,001";
  const digits = usd > 0 && usd < 0.01 ? 3 : 2;
  const amount = usd.toLocaleString("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return `≈ ${amount}`;
}

/** Pastille « 12 340 tokens · ≈ 0,04 $ » ; les tokens et le plafond sont dans l'infobulle. */
export function CostBadge({ cost }: CostBadgeProps) {
  if (!cost) {
    return <span className="text-sm text-muted-foreground">{t("session.cost.none")}</span>;
  }
  const tokens = integer.format(cost.tokens_in + cost.tokens_out);
  return (
    <span
      title={t("session.cost.title", { tokens, cap: integer.format(cost.cap_tokens) })}
      className="inline-flex items-center whitespace-nowrap rounded-full border border-border bg-card px-2.5 py-0.5 text-sm tabular-nums"
    >
      {t("session.cost.summary", { tokens, cost: formatCost(cost.cost_usd) })}
    </span>
  );
}
