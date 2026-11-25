import { Link, useNavigate, useParams } from "react-router";
import { ApiError } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { useApplication } from "../../hooks/useApplication";
import { applicationPath, BOARD_PATH } from "../../urls";
import { InterviewHub } from "../InterviewHub";

const isMissing = (error: unknown) => error instanceof ApiError && error.status === 404;

/**
 * The mock interview (`/applications/:applicationId/interview`): the settings, then
 * a written exchange, one question at a time, and the debrief; the record's past interviews below.
 * `createSocket` is only for tests.
 */
export function InterviewPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { applicationId = "" } = useParams();
  const navigate = useNavigate();
  const application = useApplication(applicationId);

  if (isMissing(application.error)) {
    return (
      <EmptyState
        as="h1"
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
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t("applications.interviewPage.title")}</h1>
        {application.data ? (
          <p className="font-medium">
            {t("applications.interviewPage.for", {
              company: application.data.company,
              title: application.data.title,
            })}
          </p>
        ) : null}
        <p className="max-w-prose text-muted-foreground">{t("applications.interviewPage.intro")}</p>
        <Link
          to={applicationPath(applicationId)}
          className="w-fit text-sm font-medium text-primary underline underline-offset-4"
        >
          {t("applications.interviewPage.back")}
        </Link>
      </header>
      <InterviewHub key={applicationId} applicationId={applicationId} createSocket={createSocket} />
    </div>
  );
}
