import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { SalaryScenarioView } from "../salaryScenarioView";
import { euros } from "./euros";

export function SalaryOutcome({
  outcome,
}: {
  outcome: NonNullable<SalaryScenarioView["outcome"]>;
}) {
  const heading = useId();
  return (
    <section aria-labelledby={heading} className="rounded-xl border bg-card p-4">
      <h3 id={heading} className="font-semibold">
        {t("applications.salaryScenario.result")}
      </h3>
      <p>{t(`applications.salaryScenario.reason.${outcome.reason}`)}</p>
      <p>{t("applications.salaryScenario.final", { amount: euros(outcome.offer) })}</p>
      <p>{t("applications.salaryScenario.remaining", { amount: euros(outcome.remaining) })}</p>
    </section>
  );
}
