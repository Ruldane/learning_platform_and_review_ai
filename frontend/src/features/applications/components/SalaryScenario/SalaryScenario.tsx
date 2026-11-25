import { useId } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SalaryScenarioView } from "../salaryScenarioView";
import { SalaryOutcome } from "./SalaryOutcome";
import { euros } from "./euros";

export function SalaryScenario({ data }: { data: SalaryScenarioView }) {
  const heading = useId();
  return (
    <div className="grid gap-3">
      <section aria-labelledby={heading} className="rounded-xl border bg-card p-4">
        <h3 id={heading} className="font-semibold">
          {t("applications.salaryScenario.source")}
        </h3>
        <p>{t("applications.salaryScenario.scope", { role: data.role, zone: data.zone })}</p>
        <p>
          {data.minimum === data.maximum
            ? t("applications.salaryScenario.amount", { amount: euros(data.minimum) })
            : t("applications.salaryScenario.range", {
                min: euros(data.minimum),
                max: euros(data.maximum),
              })}
        </p>
        <p className="text-sm text-muted-foreground">
          {t(
            data.observations === 1
              ? "applications.salaryScenario.one"
              : "applications.salaryScenario.many",
            {
              count: data.observations,
            },
          )}
        </p>
        <Link
          to={`/career/radar/${data.runId}`}
          className="text-sm text-primary underline underline-offset-4"
        >
          {t("applications.salaryScenario.open")}
        </Link>
      </section>
      <section aria-labelledby={`${heading}-rules`} className="rounded-xl border bg-card p-4">
        <h3 id={`${heading}-rules`} className="font-semibold">
          {t("applications.salaryScenario.rules")}
        </h3>
        <p>{t("applications.salaryScenario.initial", { amount: euros(data.minimum) })}</p>
        <p>{t("applications.salaryScenario.limit", { amount: euros(data.maximum) })}</p>
      </section>
      {data.outcome ? <SalaryOutcome outcome={data.outcome} /> : null}
    </div>
  );
}
