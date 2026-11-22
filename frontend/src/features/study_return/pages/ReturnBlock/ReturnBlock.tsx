import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ReturnPlan } from "../../api";
import { trainingUrl } from "../../dates";
import { ReturnSelection } from "../ReturnSelection";
import { useReturnBlock } from "./useReturnBlock";

export function ReturnBlock({ plan }: { plan: ReturnPlan | null }) {
  const { prepare, start, isWorking } = useReturnBlock();
  const error = prepare.error ?? start.error;
  return (
    <section className="flex flex-col gap-3">
      <Button
        type="button"
        variant="outline"
        className="self-start"
        aria-disabled={isWorking}
        onClick={() => {
          if (!isWorking) {
            start.reset();
            prepare.mutate();
          }
        }}
      >
        {t(plan ? "studyReturn.refresh" : "studyReturn.prepare")}
      </Button>
      {error && <p role="alert">{errorMessage(error)}</p>}
      {plan && <ReturnSelection plan={plan} />}
      {plan?.training_id && (
        <Link className="self-start underline" to={trainingUrl(plan.training_id)}>
          {t("studyReturn.resume")}
        </Link>
      )}
      {plan && !plan.training_id && (
        <Button
          type="button"
          className="self-start"
          aria-disabled={isWorking}
          onClick={() => {
            if (!isWorking) {
              prepare.reset();
              start.mutate();
            }
          }}
        >
          {t("studyReturn.start")}
        </Button>
      )}
    </section>
  );
}
