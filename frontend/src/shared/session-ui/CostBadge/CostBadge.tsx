import { t } from "@/shared/i18n/t";
import type { CostPayload } from "@/shared/realtime/types";

interface CostBadgeProps {
  cost: CostPayload | null;
}

const integer = new Intl.NumberFormat("fr-FR");

/** Deux décimales, trois sous le centime pour qu'un petit coût ne s'affiche pas « 0,00 ». */
function formatCost(usd: number): string {
  const digits = usd > 0 && usd < 0.01 ? 3 : 2;
  return usd.toLocaleString("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
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
