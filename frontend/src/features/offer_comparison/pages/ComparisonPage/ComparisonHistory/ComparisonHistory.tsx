import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { HISTORY, listComparisons } from "../../../api";

export function ComparisonHistory() {
  const list = useQuery({ queryKey: HISTORY, queryFn: ({ signal }) => listComparisons(signal) });
  return (
    <section className="grid gap-3">
      <h2 className="text-lg font-semibold">{t("offerComparison.history")}</h2>
      {list.isPending ? <LoadingState label={t("offerComparison.loading")} /> : null}
      {list.error ? <ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} /> : null}
      {list.data?.length === 0 ? <p>{t("offerComparison.empty")}</p> : null}
      {list.data?.length ? <ul className="grid gap-2">
        {list.data.map((row) => (
          <li key={row.id} className="rounded border bg-card p-3">
            <Link to={`/carriere/comparer-les-offres/${row.id}`} className="underline">
              {row.first.title ?? t("offerComparison.unknownTitle")} · {row.second.title ?? t("offerComparison.unknownTitle")}
            </Link>
          </li>
        ))}
      </ul> : null}
    </section>
  );
}
