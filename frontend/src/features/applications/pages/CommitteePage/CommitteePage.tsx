import { useNavigate, useParams } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useApplication } from "../../hooks/useApplication";
import { BOARD_PATH } from "../../urls";
import { CommitteeHeader } from "./CommitteeHeader";
import { CommitteeWorkspace } from "./CommitteeWorkspace";

const isMissing = (error: unknown) => error instanceof ApiError && error.status === 404;

/**
 * Le comité de recrutement simulé d'une candidature (`/candidatures/:applicationId/comite`) : le
 * débat à gauche, les votes, le verdict et l'avant / après à droite, sous le bandeau « Simulation,
 * pas une prédiction ». `createSocket` ne sert qu'aux tests.
 */
export function CommitteePage({ createSocket }: { createSocket?: SocketFactory }) {
  const { applicationId = "" } = useParams();
  const navigate = useNavigate();
  const application = useApplication(applicationId);

  if (isMissing(application.error)) {
    return (
      <EmptyState
        title={t("applications.drawer.notFoundTitle")}
        description={t("applications.errors.application_not_found")}
        action={{
          label: t("applications.drawer.notFoundAction"),
          onClick: () => void navigate(BOARD_PATH),
        }}
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <CommitteeHeader applicationId={applicationId} application={application.data} />
      {application.isError ? (
        <ErrorState
          message={errorMessage(application.error)}
          onRetry={() => void application.refetch()}
        />
      ) : null}
      {application.isPending ? (
        <LoadingState label={t("applications.committeePage.loading")} />
      ) : null}
      {application.data ? (
        <CommitteeWorkspace
          key={applicationId}
          applicationId={applicationId}
          postingId={application.data.posting_id}
          cvVersionId={application.data.cv_version_id}
          createSocket={createSocket}
        />
      ) : null}
    </div>
  );
}
