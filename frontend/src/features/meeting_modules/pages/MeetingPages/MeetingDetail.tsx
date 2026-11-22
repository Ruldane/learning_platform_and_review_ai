import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { meetingPath, meetingsKey, readMeeting } from "../../api";
import { MeetingWorkspace } from "./MeetingWorkspace";

export function MeetingDetail() {
  const id = useParams().moduleId ?? "";
  const detail = useQuery({
    queryKey: [...meetingsKey, id],
    queryFn: ({ signal }) => readMeeting(id, signal),
  });
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <Link to={meetingPath} className="underline">
        {t("meetingModules.back")}
      </Link>
      {detail.isPending && <LoadingState label={t("meetingModules.loading")} />}
      {detail.isError && (
        <ErrorState message={errorMessage(detail.error)} onRetry={() => void detail.refetch()} />
      )}
      {detail.data && <MeetingWorkspace key={id} module={detail.data} />}
    </main>
  );
}
