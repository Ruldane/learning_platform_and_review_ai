import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readReplay, replayBasePath, replayKey } from "../../api";
import { ReplayWorkspace } from "./ReplayWorkspace";

export function ReplayDetailPage() {
  const replayId = useParams().replayId ?? "";
  const replay = useQuery({
    queryKey: [...replayKey, replayId],
    queryFn: ({ signal }) => readReplay(replayId, signal),
  });
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <Link className="underline" to={replayBasePath}>
        {t("incidentReplay.back")}
      </Link>
      {replay.isPending && <LoadingState label={t("incidentReplay.loading")} />}
      {replay.isError && (
        <ErrorState message={errorMessage(replay.error)} onRetry={() => void replay.refetch()} />
      )}
      {replay.data && <ReplayWorkspace key={replayId} replay={replay.data} />}
    </main>
  );
}
