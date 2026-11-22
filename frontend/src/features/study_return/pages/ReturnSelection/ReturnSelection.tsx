import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { ReturnPlan } from "../../api";
import { LastFinishedBlock } from "../LastFinishedBlock";

export function ReturnSelection({ plan }: { plan: ReturnPlan }) {
  return (
    <div className="flex flex-col gap-3 rounded border border-border p-4">
      <h2 className="font-semibold">{t("studyReturn.plan")}</h2>
      <p>{t("studyReturn.shortDuration", { minutes: plan.minutes })}</p>
      {plan.skills.length > 0 && (
        <div>
          <h3 className="font-medium">{t("studyReturn.skills")}</h3>
          <ul className="list-inside list-disc">
            {plan.skills.map((item) => (
              <li key={item.id}>{item.name}</li>
            ))}
          </ul>
        </div>
      )}
      {plan.cards.length > 0 && (
        <div>
          <h3 className="font-medium">{t("studyReturn.cards")}</h3>
          <ul className="list-inside list-disc">
            {plan.cards.map((item) => (
              <li key={item.id}>{item.front}</li>
            ))}
          </ul>
          <Link className="underline" to="/etudier/revisions">
            {t("studyReturn.reviews")}
          </Link>
        </div>
      )}
      {plan.last_block && <LastFinishedBlock value={plan.last_block} />}
      {!plan.skills.length && !plan.cards.length && !plan.last_block && (
        <p>{t("studyReturn.empty")}</p>
      )}
    </div>
  );
}
