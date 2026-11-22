import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ComparisonResult } from "../../components/ComparisonResult";
import { toComparisonView } from "../../toView";
import { ComparisonEditor } from "./ComparisonEditor";
import { ComparisonHistory } from "./ComparisonHistory";
import { useComparison } from "./useComparison";

export function ComparisonPage() {
  const screen = useComparison();
  const failure = screen.criteria.error ?? screen.options.error;
  return (
    <section className="grid max-w-4xl gap-5">
      <h1 className="text-2xl font-semibold">{t("offerComparison.title")}</h1>
      {failure ? <ErrorState message={errorMessage(failure)} onRetry={() => {
        void screen.criteria.refetch();
        void screen.options.refetch();
      }} /> : null}
      {screen.criteria.isPending || screen.options.isPending ? <LoadingState label={t("offerComparison.loading")} /> : null}
      <ComparisonEditor screen={screen} />
      {screen.preview.data ? <ComparisonResult view={toComparisonView(screen.preview.data)} /> : null}
      <ComparisonHistory />
    </section>
  );
}
