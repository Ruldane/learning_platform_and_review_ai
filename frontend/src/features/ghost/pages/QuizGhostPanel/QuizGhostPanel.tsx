import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { QuizGhostProps } from "@/shared/lib/ghostPanels";
import { InlineError } from "@/shared/ui/states/InlineError";
import { fetchQuizGhost } from "../../api";
import { GhostComparison, type Metrics } from "../../components/GhostComparison";

import { toReference } from "../../toView";

export function QuizGhostPanel({ quizId, live, currentAttemptId }: QuizGhostProps) {
  const [params, setParams] = useSearchParams();
  const referenceId = params.get("fantome");
  const query = useQuery({
    queryKey: ["ghost", "quiz", quizId, referenceId],
    queryFn: ({ signal }) => fetchQuizGhost(quizId, referenceId, signal),
    refetchOnMount: "always",
    placeholderData: (previous) => previous,
  });
  if (query.isPending)
    return (
      <p role="status" className="text-sm">
        {t("ghost.loading")}
      </p>
    );
  if (!query.data) {
    return <InlineError message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  const summaries = query.data.map(toReference);
  const attempts = summaries.filter((item) => item.id !== currentAttemptId);
  const selected = attempts.find((item) => item.id === referenceId);
  const current: Metrics | null = live
    ? { duration: live.elapsedMs, errors: null, completed: live.answered, total: live.total }
    : (summaries.find((item) => item.id === currentAttemptId)?.metrics ?? null);
  return (
    <GhostComparison
      kind="quiz"
      attempts={attempts}
      selected={selected}
      current={current}
      ongoing={live !== undefined}
      onSelect={(id) => {
        const updated = new URLSearchParams(params);
        if (id) updated.set("fantome", id);
        else updated.delete("fantome");
        void setParams(updated, { replace: true, preventScrollReset: true });
      }}
    />
  );
}
