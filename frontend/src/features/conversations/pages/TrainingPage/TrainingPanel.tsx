import { Navigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { trainingPath, useTraining } from "../../hooks/useTraining";
import { useTrainingTopic } from "../../hooks/useTrainingTopic";
import { TrainingResult } from "./TrainingResult";
import { TrainingRunning } from "./TrainingRunning";
import { TrainingStart } from "./TrainingStart";

interface Props {
  studyId?: string;
  skillId: string;
  fresh: boolean;
}

export function TrainingPanel({ studyId, skillId, fresh }: Props) {
  const subject = useTrainingTopic(skillId);
  const topic = subject.data ?? "";
  const { query, launch, change, sessionId, submitted, refresh } = useTraining(
    studyId,
    skillId,
    fresh,
  );
  if (!fresh && (query.isPending || (skillId && subject.isPending))) {
    return <LoadingState label={t("training.loading")} />;
  }
  if (!fresh && query.isError && !query.data)
    return <ErrorState message={errorMessage(query.error)} onRetry={refresh} />;

  const session = fresh ? undefined : query.data;
  if (session && !studyId) return <Navigate replace to={trainingPath(session.id, skillId)} />;
  const error = launch.error ?? change.error ?? (fresh ? null : query.error);
  return (
    <div className="flex min-w-0 flex-col gap-4">
      {topic && <p>{t("training.topic", { topic })}</p>}
      {error ? <InlineError message={errorMessage(error)} /> : null}
      {!session ? (
        <TrainingStart
          busy={launch.isPending}
          onStart={(mode, lessonIds) =>
            launch.mutate({ mode, lesson_ids: lessonIds, new_conversation: true })
          }
        />
      ) : null}
      {session && session.status !== "open" ? <TrainingResult session={session} /> : null}
      {session ? (
        <TrainingRunning
          key={session.id}
          session={session}
          sessionId={sessionId}
          saving={change.isPending}
          initialText={topic ? t("training.topicQuestion", { topic }) : ""}
          onChange={(body) => change.mutate(body)}
          onSubmitted={submitted}
          onRefresh={refresh}
        />
      ) : null}
    </div>
  );
}
