import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readMarket } from "../../api";
import type { MarketFilters } from "../../types";
import { HourResult } from "../../components/HourResult";
import { QuoteTable } from "../../components/QuoteTable";
import { MarketFilter } from "./MarketFilter";

export function SkillMarketPage() {
  const [filters, setFilters] = useState<MarketFilters>({});
  const market = useQuery({
    queryKey: ["skillMarket", filters],
    queryFn: ({ signal }) => readMarket(filters, signal),
    placeholderData: (previous) => previous,
  });
  const data = market.data;
  return (
    <div className="flex max-w-4xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("skillMarket.title")}</h1>
      {market.isPending ? <LoadingState /> : null}
      {market.isError ? (
        <ErrorState message={errorMessage(market.error)} onRetry={() => void market.refetch()} />
      ) : null}
      {data ? (
        <>
          <MarketFilter
            key={data.role + "/" + data.zone}
            role={data.role}
            zone={data.zone}
            apply={setFilters}
          />
          {data.current ? (
            <p className="text-sm text-muted-foreground">
              {t("skillMarket.sample", { count: data.current.analyzed })}
              {data.indicative ? " " + t("skillMarket.indicative") : ""}
            </p>
          ) : (
            <p>{t("skillMarket.empty")}</p>
          )}
          {data.simulation ? (
            <div aria-live="polite">
              <HourResult value={data.simulation} />
            </div>
          ) : null}
          {data.quotes.length ? (
            <QuoteTable
              rows={data.quotes}
              pick={(item) => setFilters((value) => ({ ...value, skill: item.key }))}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
