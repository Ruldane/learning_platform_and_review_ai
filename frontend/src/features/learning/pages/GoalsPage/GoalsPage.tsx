import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { errorMessage } from "@/shared/api/errors";
import { GoalForm } from "../../components/GoalForm";
import { GoalList } from "../../components/GoalList";
import { useCreateGoal } from "../../hooks/useCreateGoal";
import { useGoals } from "../../hooks/useGoals";
import { toGoalRow } from "../../toView";

/**
 * Objectifs (`/apprendre/objectifs`) : saisir un objectif lance le Conseil et l'ouvre ; en dessous,
 * les objectifs déjà saisis avec leur statut et leurs liens (Conseil, programme).
 */
export function GoalsPage() {
  const goals = useGoals();
  const create = useCreateGoal();
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("learning.goals.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("learning.goals.intro")}</p>
      </header>
      <GoalForm busy={create.pending} onSubmit={create.create} />
      {create.error ? <InlineError message={create.error} /> : null}
      <section aria-labelledby="goals-list-title" className="flex flex-col gap-3">
        <h2 id="goals-list-title" className="text-lg font-semibold">
          {t("learning.goals.list.label")}
        </h2>
        {goals.isPending ? <LoadingState label={t("learning.goals.list.loading")} /> : null}
        {goals.isError ? (
          <ErrorState message={errorMessage(goals.error)} onRetry={() => void goals.refetch()} />
        ) : null}
        {goals.data?.length === 0 ? (
          <EmptyState
            title={t("learning.goals.list.emptyTitle")}
            description={t("learning.goals.list.emptyDescription")}
          />
        ) : null}
        {goals.data && goals.data.length > 0 ? (
          <GoalList goals={goals.data.map(toGoalRow)} />
        ) : null}
      </section>
    </div>
  );
}
