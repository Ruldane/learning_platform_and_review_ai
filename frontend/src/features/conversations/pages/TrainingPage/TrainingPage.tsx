import { Navigate, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { trainingPath, useTraining } from "../../hooks/useTraining";
import { TrainingResult } from "./TrainingResult";
import { TrainingRunning } from "./TrainingRunning";
import { TrainingStart } from "./TrainingStart";

export function TrainingPage() {
  const { studyId } = useParams();
  const { query, launch, change, sessionId, submitted, refresh } = useTraining(studyId);
  if (query.isPending) return <LoadingState label={t("training.loading")} />;
  if (query.isError && !query.data)
    return <ErrorState message={errorMessage(query.error)} onRetry={refresh} />;

  const session = query.data;
  if (session && !studyId) return <Navigate replace to={trainingPath(session.id)} />;
  const error = launch.error ?? change.error ?? query.error;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("training.title")}</h1>
      {error ? <InlineError message={errorMessage(error)} /> : null}
      {!session ? (
        <TrainingStart busy={launch.isPending} onStart={(mode) => launch.mutate(mode)} />
      ) : null}
      {session && session.status !== "open" ? <TrainingResult session={session} /> : null}
      {session?.status === "open" ? (
        <TrainingRunning
          key={session.id}
          session={session}
          sessionId={sessionId}
          saving={change.isPending}
          onChange={(body) => change.mutate(body)}
          onSubmitted={submitted}
          onRefresh={refresh}
        />
      ) : null}
    </div>
  );
}
