import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readSite } from "../../api";
import { PortfolioCandidates } from "./PortfolioCandidates";
import { PortfolioDraft } from "./PortfolioDraft";
import { PortfolioPublished } from "./PortfolioPublished";

export function PortfolioPage() {
  const heading = useRef<HTMLHeadingElement>(null);
  const site = useQuery({ queryKey: ["portfolio"], queryFn: ({ signal }) => readSite(signal) });
  const reload = () => void site.refetch();
  return (
    <section className="flex max-w-4xl flex-col gap-5">
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold">
        {t("portfolio.title")}
      </h1>
      {site.isPending && <LoadingState />}
      {site.isError && <ErrorState message={errorMessage(site.error)} onRetry={reload} />}
      {site.data && (
        <>
          {site.data.publication && (
            <PortfolioPublished
              key={`published:${site.data.publication.revision_id}`}
              value={site.data.publication}
              reload={reload}
              restoreFocus={() => heading.current?.focus()}
            />
          )}
          <PortfolioCandidates candidates={site.data.candidates} reload={reload} />
          {site.data.draft && (
            <PortfolioDraft
              key={`draft:${site.data.draft.id}`}
              value={site.data.draft}
              current={site.data.publication}
              reload={reload}
            />
          )}
        </>
      )}
    </section>
  );
}
