import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SessionStatus } from "@/shared/realtime/types";
import { Button, buttonVariants } from "@/shared/ui/button";

interface ReplanEndProps {
  programId: string;
  status: SessionStatus;
  /** Le message d'échec de la session, quand elle s'est arrêtée sur une erreur. */
  failure: string | null;
  /** Ce que January a décidé de la proposition, quand l'historique le dit. */
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
 * La fin d'une replanification : ce qui s'est passé (plan accepté, gardé, annulé, arrêt), le retour
 * au programme et une nouvelle demande.
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
        <Link to={`/apprendre/programme/${programId}`} className={buttonVariants()}>
          {t("replan.back")}
        </Link>
        <Button variant="outline" onClick={onAgain}>
          {t("replan.run.again")}
        </Button>
      </div>
    </div>
  );
}
