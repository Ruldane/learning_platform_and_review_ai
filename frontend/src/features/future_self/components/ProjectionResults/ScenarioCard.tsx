import { t } from "@/shared/i18n/t";
import { formatMinutes, longDay } from "@/shared/lib/format";
import type { ScenarioView } from "../viewTypes";

export function ScenarioCard({ scenario, target }: { scenario: ScenarioView; target: number }) {
  const id = "projection-" + scenario.id;
  const pace =
    scenario.weeklyMinutes === null
      ? t("futureSelf.unavailable")
      : t("futureSelf.pace", { duration: formatMinutes(scenario.weeklyMinutes) });
  return (
    <section aria-labelledby={id} className="grid gap-2 rounded-xl border bg-card p-4">
      <div>
        <h3 id={id} className="font-semibold">
          {scenario.title}
        </h3>
        <p className="text-sm text-muted-foreground">{pace}</p>
      </div>
      <dl className="grid gap-1 text-sm">
        <dt>{t("futureSelf.date", { percent: target })}</dt>
        <dd className="font-medium">
          {scenario.targetDate ? (
            <time dateTime={scenario.targetDate}>{longDay(scenario.targetDate)}</time>
          ) : (
            t(
              scenario.weeklyMinutes === null || scenario.projectedPercent === null
                ? "futureSelf.unavailable"
                : "futureSelf.notReached",
            )
          )}
        </dd>
        <dt className="mt-1">{t("futureSelf.final")}</dt>
        <dd className="font-medium">
          {scenario.projectedPercent === null
            ? t("futureSelf.unavailable")
            : `${scenario.projectedPercent} %`}
        </dd>
      </dl>
    </section>
  );
}
