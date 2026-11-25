import { useNavigate, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useProject } from "../../hooks/useProject";
import { PORTFOLIO_PATH } from "../../paths";
import { BackLink } from "./BackLink";
import { ProjectView } from "./ProjectView";

/**
 * Un projet (`/skills/portfolio/:projectId`) : l'énoncé, le rendu et son suivi, l'évaluation,
 * puis, une fois validé, les brouillons et l'ajout au profil maître. `createSocket` ne sert
 * qu'aux tests.
 */
export function ProjectPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const { query, missing } = useProject(projectId);
  if (query.data)
    return <ProjectView key={query.data.id} project={query.data} createSocket={createSocket} />;
  return (
    <div className="flex flex-col gap-4">
      <BackLink />
      {missing ? null : (
        <h1 className="text-2xl font-semibold">{t("projects.page.genericTitle")}</h1>
      )}
      {query.isPending ? <LoadingState label={t("projects.page.loading")} /> : null}
      {missing ? (
        <EmptyState
          as="h1"
          title={t("projects.page.notFoundTitle")}
          description={t("projects.page.notFoundText")}
          action={{
            label: t("projects.page.notFoundAction"),
            onClick: () => void navigate(PORTFOLIO_PATH),
          }}
        />
      ) : null}
      {query.isError && !missing ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
    </div>
  );
}
