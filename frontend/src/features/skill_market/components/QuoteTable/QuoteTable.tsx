import { t } from "@/shared/i18n/t";
import type { QuoteView as Quote } from "../viewTypes";
import { QuoteRow } from "./QuoteRow";

export function QuoteTable({
  rows,
  pick,
}: {
  rows: readonly Quote[];
  pick: (quote: Quote) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{t("skillMarket.caption")}</caption>
        <thead className="bg-muted">
          <tr>
            <th scope="col" className="p-3">
              {t("skillMarket.skill")}
            </th>
            <th scope="col" className="p-3">
              {t("skillMarket.demand")}
            </th>
            <th scope="col" className="p-3">
              {t("skillMarket.change")}
            </th>
            <th scope="col" className="p-3">
              {t("skillMarket.study")}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((quote) => (
            <QuoteRow key={quote.key} quote={quote} pick={pick} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
