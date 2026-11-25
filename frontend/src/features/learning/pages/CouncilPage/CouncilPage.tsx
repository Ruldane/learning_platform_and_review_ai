import { Link, useParams } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useGoal } from "../../hooks/useGoal";
import { CouncilLayout } from "./CouncilLayout";

/**
 * A goal's Council (`/learn/goals/:goalId/council`). The goal gives the session
 * of the Council: reloading the page rejoins the same session, the stream replays the events.
 * `createSocket` is only for tests (fake WebSocket).
 */
export function CouncilPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { goalId = "" } = useParams();
  const goal = useGoal(goalId);
  const missing = goal.error instanceof ApiError && goal.error.status === 404;

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold">{t("learning.council.title")}</h1>
        {goal.data ? (
          <p className="mt-1 text-muted-foreground">
            <span className="sr-only">{t("learning.council.goalLabel")} : </span>
            {goal.data.text}
          </p>
        ) : null}
      </header>
      {goal.isPending ? <LoadingState label={t("learning.council.loading")} /> : null}
      {goal.isError && missing ? (
        <EmptyState
          title={t("learning.council.notFoundTitle")}
          description={t("learning.council.notFoundDescription")}
        />
      ) : null}
      {goal.isError && !missing ? (
        <ErrorState message={errorMessage(goal.error)} onRetry={() => void goal.refetch()} />
      ) : null}
      {goal.data?.council_session_id ? (
        <CouncilLayout
          key={goal.data.council_session_id}
          goal={goal.data}
          sessionId={goal.data.council_session_id}
          createSocket={createSocket}
        />
      ) : null}
      {goal.data && !goal.data.council_session_id ? (
        <EmptyState
          title={t("learning.council.noSessionTitle")}
          description={t("learning.council.noSessionDescription")}
        />
      ) : null}
      {goal.isError || (goal.data && !goal.data.council_session_id) ? (
        <Link to="/learn/goals" className="self-start text-sm underline">
          {t("learning.council.goalsLink")}
        </Link>
      ) : null}
    </div>
  );
}
