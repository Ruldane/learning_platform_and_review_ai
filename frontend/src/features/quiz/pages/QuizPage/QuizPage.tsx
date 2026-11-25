import type { ComponentType } from "react";
import type { QuizGhostProps } from "@/shared/lib/ghostPanels";
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
  /** Re-read intervals, in ms (shortened by the tests). */
  preparePollMs?: number;
  gradePollMs?: number;
  GhostPanel?: ComponentType<QuizGhostProps>;
}

/**
 * A quiz (`/study/quiz/:quizId`). Being prepared: a wait (re-read every 3 s, 40 times). Ready:
 * the form, then the grade (re-read every 2 s, 90 times) and the result. Failed: retry the
 * preparation. A failed background re-read is reported inline, without replacing the page.
 */
export function QuizPage({
  preparePollMs = PREPARE_POLL_MS,
  gradePollMs = GRADE_POLL_MS,
  GhostPanel,
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
          action={{ label: t("quiz.page.back"), onClick: () => void navigate("/study/quiz") }}
        />
      );
    }
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  return (
    <div className="flex flex-col gap-4">
      <nav>
        <Link to="/study/quiz" className="text-sm underline underline-offset-2">
          {t("quiz.page.back")}
        </Link>
      </nav>
      <h1 className="text-2xl font-semibold">{query.data.title}</h1>
      {query.isError && !query.isFetching ? (
        <InlineError message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      <QuizBody
        quiz={query.data}
        query={query}
        budget={budget}
        gradePollMs={gradePollMs}
        GhostPanel={GhostPanel}
      />
    </div>
  );
}
