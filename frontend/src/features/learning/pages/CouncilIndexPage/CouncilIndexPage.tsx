import { Navigate, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useGoals } from "../../hooks/useGoals";
import { councilPath } from "../../hooks/useCreateGoal";

/**
 * Conseil (`/apprendre/conseil`) : ouvre le Conseil de l'objectif le plus récent ; sans objectif,
 * invite à en saisir un.
 */
export function CouncilIndexPage() {
  const goals = useGoals();
  const navigate = useNavigate();
  const latest = goals.data?.[0];

  if (goals.isPending) return <LoadingState label={t("learning.council.indexLoading")} />;
  if (goals.isError) {
    return <ErrorState message={errorMessage(goals.error)} onRetry={() => void goals.refetch()} />;
  }
  if (latest) return <Navigate to={councilPath(latest.id)} replace />;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("learning.council.title")}</h1>
      <EmptyState
        title={t("learning.council.indexEmptyTitle")}
        description={t("learning.council.indexEmptyDescription")}
        action={{
          label: t("learning.council.indexEmptyAction"),
          onClick: () => void navigate("/apprendre/objectifs"),
        }}
      />
    </div>
  );
}
