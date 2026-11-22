import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { fetchProjection } from "../../api";
import { ProjectionForm } from "../../components/ProjectionForm";
import { ProjectionResults } from "../../components/ProjectionResults";
import type { ProjectionChoices } from "../../components/viewTypes";
import { toProjectionQuery, toProjectionView } from "../../toView";
import type { ProjectionQuery } from "../../types";

export function ProjectionPage() {
  const [query, setQuery] = useState<ProjectionQuery>({});
  const projection = useQuery({
    queryKey: ["future-self", query],
    queryFn: ({ signal }) => fetchProjection(query, signal),
    placeholderData: keepPreviousData,
  });

  function compare(choices: ProjectionChoices) {
    const next = toProjectionQuery(choices);
    if (JSON.stringify(next) === JSON.stringify(query)) {
      void projection.refetch();
    } else {
      setQuery(next);
    }
  }

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold">{t("futureSelf.title")}</h1>
      <ProjectionForm
        role={projection.data?.role ?? null}
        zone={projection.data?.zone ?? ""}
        target={projection.data?.target_percent ?? 60}
        onCompare={compare}
      />
      {projection.isFetching ? <LoadingState label={t("futureSelf.loading")} /> : null}
      {projection.isError ? (
        <ErrorState
          message={errorMessage(projection.error)}
          onRetry={() => void projection.refetch()}
        />
      ) : null}
      {projection.data ? (
        <div aria-busy={projection.isFetching}>
          <ProjectionResults projection={toProjectionView(projection.data)} />
        </div>
      ) : null}
    </div>
  );
}
