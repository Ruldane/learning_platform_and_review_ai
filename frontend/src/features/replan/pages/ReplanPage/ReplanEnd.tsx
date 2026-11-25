import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SessionStatus } from "@/shared/realtime/types";
import { Button, buttonVariants } from "@/shared/ui/button";

interface ReplanEndProps {
  programId: string;
  status: SessionStatus;
  /** The session's failure message, when it stopped on an error. */
  failure: string | null;
  /** What January decided about the proposal, when the history says so. */
  decision: "accepted" | "refused" | null;
  onAgain: () => void;
}

const OUTCOME = {
  completed: "replan.run.completed",
  failed: "replan.run.failed",
  cancelled: "replan.run.cancelled",
  accepted: "replan.run.accepted",
  refused: "replan.run.refused",
} as const;

/**
 * The end of a replan: what happened (plan accepted, kept, cancelled, stopped), the return
 * to the program and a new request.
 */
export function ReplanEnd({ programId, status, failure, decision, onAgain }: ReplanEndProps) {
  const outcome =
    status === "failed" || status === "cancelled"
      ? OUTCOME[status]
      : decision !== null
        ? OUTCOME[decision]
        : OUTCOME.completed;
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <p role="status" className="font-semibold">
        {t(outcome)}
      </p>
      {failure ? <p className="text-sm text-destructive">{failure}</p> : null}
      <div className="flex flex-wrap gap-2">
        <Link to={`/learn/programs/${programId}`} className={buttonVariants()}>
          {t("replan.back")}
        </Link>
        <Button variant="outline" onClick={onAgain}>
          {t("replan.run.again")}
        </Button>
      </div>
    </div>
  );
}
