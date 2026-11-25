import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { QuizList } from "../../components/QuizList";
import { useLatestProgram, useQuizList } from "../../hooks/useQuizList";
import { useStartQuiz } from "../../hooks/useStartQuiz";

/**
 * Quiz (`/study/quiz`): the modules of the most recent program, their best score and
 * the quiz action (prepare, take, redo). « Préparer » opens the quiz page, which waits for the
 * end of the preparation. `pollMs` (re-read while a quiz is being prepared) is for tests only.
 */
export function QuizIndexPage({ pollMs }: { pollMs?: number }) {
  const navigate = useNavigate();
  const program = useLatestProgram();
  const quizzes = useQuizList(program.data?.id, pollMs);
  const starter = useStartQuiz();
  const failed = [program, quizzes].find((query) => query.isError);

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold">{t("quiz.index.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("quiz.index.intro")}</p>
      </header>
      {failed ? (
        <ErrorState message={errorMessage(failed.error)} onRetry={() => void failed.refetch()} />
      ) : null}
      {program.isPending || (program.data && quizzes.isPending) ? (
        <LoadingState label={t("quiz.index.loading")} />
      ) : null}
      {program.isSuccess && program.data === null ? (
        <EmptyState
          title={t("quiz.index.noProgramTitle")}
          description={t("quiz.index.noProgramDescription")}
          action={{
            label: t("quiz.index.noProgramAction"),
            onClick: () => void navigate("/learn/council"),
          }}
        />
      ) : null}
      {starter.error ? <InlineError message={starter.error} /> : null}
      {quizzes.data ? (
        <QuizList
          items={quizzes.data}
          pendingModuleId={starter.pendingModuleId}
          onPrepare={(moduleId, source) => void starter.prepare(moduleId, source)}
          onOpen={(quizId) => void navigate(`/study/quiz/${quizId}`)}
        />
      ) : null}
    </div>
  );
}
