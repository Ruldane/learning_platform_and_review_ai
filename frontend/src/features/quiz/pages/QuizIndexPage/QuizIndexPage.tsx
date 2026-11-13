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
 * Quiz (`/etudier/quiz`) : les modules du programme le plus récent, leur meilleur score et
 * l'action du quiz (préparer, passer, refaire). « Préparer » ouvre la page du quiz, qui attend la
 * fin de la préparation. `pollMs` (relecture tant qu'un quiz se prépare) ne sert qu'aux tests.
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
            onClick: () => void navigate("/apprendre/conseil"),
          }}
        />
      ) : null}
      {starter.error ? <InlineError message={starter.error} /> : null}
      {quizzes.data ? (
        <QuizList
          items={quizzes.data}
          pendingModuleId={starter.pendingModuleId}
          onPrepare={(moduleId) => void starter.prepare(moduleId)}
          onOpen={(quizId) => void navigate(`/etudier/quiz/${quizId}`)}
        />
      ) : null}
    </div>
  );
}
