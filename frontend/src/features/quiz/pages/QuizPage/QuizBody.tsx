import type { ComponentType } from "react";
import type { QuizGhostProps } from "@/shared/lib/ghostPanels";
import type { UseQueryResult } from "@tanstack/react-query";
import type { PollingBudget } from "@/shared/lib/usePollingBudget";
import type { QuizOut } from "../../types";
import { QuizFailed } from "./QuizFailed";
import { QuizPreparing } from "./QuizPreparing";
import { QuizTaking } from "./QuizTaking";

interface QuizBodyProps {
  quiz: QuizOut;
  query: UseQueryResult<QuizOut>;
  budget: PollingBudget;
  gradePollMs: number;
  GhostPanel?: ComponentType<QuizGhostProps>;
}

/** What the page shows for the quiz's state: preparation, failure, or the form. */
export function QuizBody({ quiz, query, budget, gradePollMs, GhostPanel }: QuizBodyProps) {
  if (quiz.status === "generating") {
    return (
      <QuizPreparing
        late={budget.exhausted}
        onKeepWaiting={() => {
          budget.restart();
          void query.refetch();
        }}
      />
    );
  }
  if (quiz.status === "failed") {
    return (
      <QuizFailed
        moduleId={quiz.module_id}
        reason={quiz.failure_reason}
        onRelaunched={() => void query.refetch()}
      />
    );
  }
  return (
    <QuizTaking
      key={quiz.id}
      quiz={quiz}
      refreshing={query.isFetching}
      gradePollMs={gradePollMs}
      GhostPanel={GhostPanel}
    />
  );
}
