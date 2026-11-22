import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { QuoteView as Quote } from "../viewTypes";

const RATE = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const TREND = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});

export function QuoteRow({ quote, pick }: { quote: Quote; pick: (quote: Quote) => void }) {
  return (
    <tr className="border-t">
      <th scope="row" className="p-3 font-medium">
        {quote.name}
      </th>
      <td className="p-3 tabular-nums">
        {t("skillMarket.percent", { value: RATE.format(quote.demand_percent) })}
      </td>
      <td className="p-3 tabular-nums">
        {quote.change_points === null
          ? t("skillMarket.noTrend")
          : TREND.format(quote.change_points)}
      </td>
      <td className="p-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => pick(quote)}
          aria-label={t("skillMarket.simulateSkill", { name: quote.name })}
        >
          {t(quote.opportunity ? "skillMarket.opportunity" : "skillMarket.simulate")}
        </Button>
      </td>
    </tr>
  );
}
