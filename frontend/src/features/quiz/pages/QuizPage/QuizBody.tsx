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
}

/** Ce que la page montre selon l'état du quiz : préparation, échec ou formulaire. */
export function QuizBody({ quiz, query, budget, gradePollMs }: QuizBodyProps) {
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
  return <QuizTaking quiz={quiz} refreshing={query.isFetching} gradePollMs={gradePollMs} />;
}
