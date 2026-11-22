import { useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { IncidentList } from "../../components/IncidentList";
import { OncallStart } from "../../components/OncallStart";
import { useOncall } from "../../hooks/useOncall";
import { IncidentDetail } from "./IncidentDetail";

export function OncallPage() {
  const { incidentId = "" } = useParams();
  const { query, incident, start, activity } = useOncall(incidentId);
  const current = incidentId ? incident : query;
  if (current.isPending) return <LoadingState label={t("oncall.loading")} />;
  if (current.isError && current.data === undefined) {
    return (
      <ErrorState message={errorMessage(current.error)} onRetry={() => void current.refetch()} />
    );
  }
  const error = activity.error ?? start.error;
  return (
    <div className="flex max-w-3xl flex-col gap-5">
      {error && <InlineError message={errorMessage(error)} />}
      {incidentId && incident.data ? (
        <IncidentDetail
          incident={incident.data}
          busy={activity.isPending}
          onAct={activity.mutate}
        />
      ) : (
        <>
          <h1 className="text-2xl font-semibold">{t("oncall.title")}</h1>
          <p>{t("oncall.description")}</p>
          <OncallStart busy={start.isPending} onStart={start.mutate} />
          <IncidentList incidents={query.data ?? []} />
        </>
      )}
    </div>
  );
}
