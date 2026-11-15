import { useNavigate } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useApplication } from "../../hooks/useApplication";
import { useKit } from "../../hooks/useKit";
import { BOARD_PATH } from "../../urls";
import { KitBody } from "./KitBody";
import { KitHeader } from "./KitHeader";

const isMissing = (error: unknown) => error instanceof ApiError && error.status === 404;

interface KitContentProps {
  applicationId: string;
  createSocket?: SocketFactory;
}

/** La page du kit : l'en-tête de la fiche, puis le kit lu (chargement, panne, ou le kit lui-même). */
export function KitContent({ applicationId, createSocket }: KitContentProps) {
  const navigate = useNavigate();
  const application = useApplication(applicationId);
  const kit = useKit(applicationId);

  if (isMissing(application.error) || isMissing(kit.error)) {
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
      <KitHeader applicationId={applicationId} application={application.data} />
      {kit.isPending ? <LoadingState label={t("applications.kitPage.loading")} /> : null}
      {kit.isError ? (
        <ErrorState message={errorMessage(kit.error)} onRetry={() => void kit.refetch()} />
      ) : null}
      {kit.isSuccess ? (
        <KitBody applicationId={applicationId} kit={kit.data} createSocket={createSocket} />
      ) : null}
    </div>
  );
}
