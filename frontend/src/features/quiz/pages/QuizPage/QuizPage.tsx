import { Link, useNavigate, useParams } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { GRADE_POLL_MS } from "../../hooks/useAttempt";
import { PREPARE_POLL_MS, useQuiz } from "../../hooks/useQuiz";
import { QuizBody } from "./QuizBody";

interface QuizPageProps {
  /** Intervalles de relecture, en ms (réduits par les tests). */
  preparePollMs?: number;
  gradePollMs?: number;
}

/**
 * Un quiz (`/etudier/quiz/:quizId`). En préparation : attente (relue toutes les 3 s, 40 fois). Prêt :
 * le formulaire, puis la note (relue toutes les 2 s, 90 fois) et le résultat. Raté : relancer la
 * préparation. Une relecture ratée en arrière-plan se dit en ligne, sans remplacer la page.
 */
export function QuizPage({
  preparePollMs = PREPARE_POLL_MS,
  gradePollMs = GRADE_POLL_MS,
}: QuizPageProps) {
  const { quizId = "" } = useParams();
  const navigate = useNavigate();
  const { query, budget } = useQuiz(quizId, preparePollMs);

  if (query.isPending) return <LoadingState label={t("quiz.page.loading")} />;
  if (query.isError && query.data === undefined) {
    if (query.error instanceof ApiError && query.error.status === 404) {
      return (
        <EmptyState
          title={t("quiz.page.notFoundTitle")}
          description={t("quiz.page.notFoundDescription")}
          action={{ label: t("quiz.page.back"), onClick: () => void navigate("/etudier/quiz") }}
        />
      );
    }
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  return (
    <div className="flex flex-col gap-4">
      <nav>
        <Link to="/etudier/quiz" className="text-sm underline underline-offset-2">
          {t("quiz.page.back")}
        </Link>
      </nav>
      <h1 className="text-2xl font-semibold">{query.data.title}</h1>
      {query.isError && !query.isFetching ? (
        <InlineError message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      <QuizBody quiz={query.data} query={query} budget={budget} gradePollMs={gradePollMs} />
    </div>
  );
}
