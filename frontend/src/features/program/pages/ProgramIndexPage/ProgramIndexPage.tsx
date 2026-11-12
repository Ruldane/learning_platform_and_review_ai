import { Navigate, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { usePrograms } from "../../hooks/usePrograms";

/**
 * Programme (`/apprendre/programme`) : ouvre le programme le plus récent ; sans programme, renvoie
 * au Conseil, qui le fait naître.
 */
export function ProgramIndexPage() {
  const programs = usePrograms();
  const navigate = useNavigate();
  const latest = programs.data?.[0];

  if (programs.isPending) return <LoadingState label={t("program.page.indexLoading")} />;
  if (programs.isError) {
    return (
      <ErrorState message={errorMessage(programs.error)} onRetry={() => void programs.refetch()} />
    );
  }
  if (latest) return <Navigate to={`/apprendre/programme/${latest.id}`} replace />;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("program.nav.program")}</h1>
      <EmptyState
        title={t("program.page.indexEmptyTitle")}
        description={t("program.page.indexEmptyDescription")}
        action={{
          label: t("program.page.indexEmptyAction"),
          onClick: () => void navigate("/apprendre/conseil"),
        }}
      />
    </div>
  );
}
