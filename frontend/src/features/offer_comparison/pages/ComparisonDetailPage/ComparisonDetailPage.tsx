import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { detailKey, readComparison } from "../../api";
import { ComparisonResult } from "../../components/ComparisonResult";
import { toComparisonView } from "../../toView";

export function ComparisonDetailPage() {
  const { scenarioId = "" } = useParams();
  const row = useQuery({
    queryKey: detailKey(scenarioId),
    queryFn: ({ signal }) => readComparison(scenarioId, signal),
  });
  return (
    <section className="grid max-w-4xl gap-5">
      <Link className="w-fit underline" to="/career/offer-comparison">
        {t("offerComparison.back")}
      </Link>
      <h1 className="text-2xl font-semibold">{t("offerComparison.recorded")}</h1>
      {row.isPending ? <LoadingState label={t("offerComparison.loading")} /> : null}
      {row.error ? <ErrorState message={errorMessage(row.error)} onRetry={() => void row.refetch()} /> : null}
      {row.data ? <ComparisonResult view={toComparisonView(row.data.result)} /> : null}
    </section>
  );
}
