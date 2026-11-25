import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { PlanFailure, PlanOutcome } from "../../hooks/usePlanGap";

interface PlanResultProps {
  outcome: PlanOutcome | null;
  failure: PlanFailure | null;
}

const replanHref = (programId: string | null) =>
  programId === null ? "/learn/programs" : `/learn/programs/${programId}/replan`;

/**
 * Outcome of « Ajouter au planning »: a link to the replan (started or already
 * open), or a readable refusal. Without a validated program, the outcome is to create a goal.
 */
export function PlanResult({ outcome, failure }: PlanResultProps) {
  if (outcome) {
    return (
      <div role="status" className="flex flex-col items-start gap-2 rounded-xl border bg-card p-3">
        <p className="text-sm">
          {t(outcome.kind === "started" ? "gap.posting.planStarted" : "gap.posting.planOpen")}
        </p>
        <Link to={replanHref(outcome.programId)} className={buttonVariants({ size: "sm" })}>
          {t("gap.posting.planLink")}
        </Link>
      </div>
    );
  }
  if (!failure) return null;
  return (
    <div className="flex flex-col items-start gap-2">
      <InlineError message={failure.message} />
      {failure.code === "no_program" ? (
        <Link to="/learn/goals" className={buttonVariants({ size: "sm" })}>
          {t("gap.posting.planNoProgram")}
        </Link>
      ) : null}
    </div>
  );
}
