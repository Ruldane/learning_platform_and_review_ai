import { t } from "@/shared/i18n/t";
import { formatUsd } from "@/shared/lib/format";
import type { CostPayload } from "@/shared/realtime/types";

interface CostBadgeProps {
  cost: CostPayload | null;
}

const integer = new Intl.NumberFormat("en-GB");

function formatCost(usd: number): string {
  const cost = formatUsd(usd);
  return cost.startsWith("<") ? cost : `≈ ${cost}`;
}

/** Shows token usage and the estimated cost. The tooltip includes the token cap. */
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
