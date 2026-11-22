import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { investigationsKey, investigationsPath, readInvestigation } from "../../api";
import { InvestigationWorkspace } from "./InvestigationWorkspace";

export function InvestigationDetail() {
  const id = useParams().investigationId ?? "";
  const detail = useQuery({
    queryKey: [...investigationsKey, id],
    queryFn: ({ signal }) => readInvestigation(id, signal),
  });
  return (
    <main className="mx-auto grid max-w-4xl gap-4 p-4">
      <Link className="underline" to={investigationsPath}>
        {t("dataInvestigation.back")}
      </Link>
      {detail.isPending && <LoadingState label={t("dataInvestigation.loading")} />}
      {detail.isError && (
        <ErrorState message={errorMessage(detail.error)} onRetry={() => void detail.refetch()} />
      )}
      {detail.data && <InvestigationWorkspace key={id} study={detail.data} />}
    </main>
  );
}
