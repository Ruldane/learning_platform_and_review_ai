import { useMemo } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ExerciseForm } from "../../components/ExerciseForm";
import { useExercises } from "../../hooks/useExercises";
import { useHomeActions } from "../../hooks/useHomeActions";
import { useSessions } from "../../hooks/useSessions";
import { toExerciseViews, toFreeSessions } from "../../toView";
import { ExerciseList } from "./ExerciseList";
import { FreeSessions } from "./FreeSessions";
import { GenerateRun } from "./GenerateRun";

interface IdeHomePageProps {
  /** For tests: the stream of the session writing the exercise. */
  createSocket?: SocketFactory;
}

/**
 * Code: write or generate an exercise, work on those in the list (their state as
 * text: to do, in progress, passed), or open a free session.
 */
export function IdeHomePage({ createSocket }: IdeHomePageProps) {
  const exercises = useExercises();
  const sessions = useSessions();
  const actions = useHomeActions();
  const views = useMemo(
    () => toExerciseViews(exercises.data ?? [], sessions.data ?? []),
    [exercises.data, sessions.data],
  );
  const free = useMemo(() => toFreeSessions(sessions.data ?? []), [sessions.data]);
  return (
    <div className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">{t("ide.home.title")}</h1>
        <p className="mt-1 max-w-prose text-muted-foreground">{t("ide.home.intro")}</p>
      </header>
      <ExerciseForm
        creating={actions.creating}
        generating={actions.generating}
        notice={actions.notice}
        error={actions.formError}
        onCreate={actions.create}
        launchMenu={actions.launchMenu}
        onGenerate={({ topic, level }) => actions.generate(topic, level)}
      />
      {actions.generated ? (
        <GenerateRun
          key={actions.generated.session_id}
          sessionId={actions.generated.session_id}
          createSocket={createSocket}
        />
      ) : null}
      <ExerciseList
        exercises={views}
        loading={exercises.isPending}
        error={exercises.error}
        busy={actions.opening}
        onRetry={() => void exercises.refetch()}
        onOpen={(exercise) => void actions.open(exercise.id, exercise.sessionId)}
      />
      <FreeSessions
        sessions={free}
        busy={actions.opening}
        onStart={() => void actions.open(null, null)}
        onResume={(id) => void actions.open(null, id)}
      />
      {actions.openError ? <InlineError message={actions.openError} /> : null}
    </div>
  );
}
