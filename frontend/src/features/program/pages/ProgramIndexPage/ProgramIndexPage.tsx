import { Navigate, useNavigate, useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ProgramList } from "../../components/ProgramList";
import { usePrograms } from "../../hooks/usePrograms";
import { toProgramSummaryView } from "../../toView";

/**
 * Programs (`/learn/programs`): the list to choose from once there are several (or with
 * `?list`); a single program opens directly; without one, a link back to the Council.
 */
export function ProgramIndexPage() {
  const programs = usePrograms();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const list = programs.data ?? [];

  if (programs.isPending) return <LoadingState label={t("program.page.indexLoading")} />;
  if (programs.isError) {
    return (
      <ErrorState message={errorMessage(programs.error)} onRetry={() => void programs.refetch()} />
    );
  }
  const [only] = list;
  if (only && list.length === 1 && !params.has("list") && !params.has("liste")) {
    return <Navigate to={`/learn/programs/${only.id}`} replace />;
  }
  if (list.length > 0) {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{t("program.page.listTitle")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("program.page.listIntro")}</p>
        </div>
        <ProgramList programs={list.map(toProgramSummaryView)} />
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("program.nav.program")}</h1>
      <EmptyState
        title={t("program.page.indexEmptyTitle")}
        description={t("program.page.indexEmptyDescription")}
        action={{
          label: t("program.page.indexEmptyAction"),
          onClick: () => void navigate("/learn/council"),
        }}
      />
    </div>
  );
}
