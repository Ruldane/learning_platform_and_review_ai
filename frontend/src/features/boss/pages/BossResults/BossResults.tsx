import type { components } from "@/shared/api/schema";
import { t } from "@/shared/i18n/t";

interface BossResultsProps {
  grade: components["schemas"]["BossGrade"];
  proved: boolean;
}

export function BossResults({ grade, proved }: BossResultsProps) {
  const rubric = ["readability", "maintenance"] as const;
  return (
    <section aria-labelledby="boss-grade" className="flex flex-col gap-3">
      <h2 id="boss-grade" className="text-xl font-semibold">
        {t("boss.grade")}
      </h2>
      <dl className="flex flex-col gap-3">
        <div>
          <dt className="font-semibold">{t("boss.total")}</dt>
          <dd>{t("boss.score", { value: grade.total, max: 20 })}</dd>
        </div>
        <div>
          <dt className="font-semibold">{t("boss.functionality")}</dt>
          <dd>{t("boss.score", { value: grade.functionality, max: 10 })}</dd>
        </div>
        {rubric.map((key) => (
          <div key={key}>
            <dt className="font-semibold">{t(`boss.${key}`)}</dt>
            <dd>{t("boss.score", { value: grade.rubric[key].score, max: 5 })}</dd>
            <dd>{grade.rubric[key].feedback}</dd>
          </div>
        ))}
      </dl>
      <h3 className="font-semibold">{t("boss.checks")}</h3>
      {grade.diagnostic.outcome === "timeout" && <p>{t("boss.timeout")}</p>}
      <ul className="list-disc pl-6">
        {grade.diagnostic.checks.map((check) => (
          <li key={check.label}>
            {check.label} · {t(check.passed ? "boss.passed" : "boss.failed")}
          </li>
        ))}
      </ul>
      {proved && (
        <p role="status" className="font-semibold">
          {t("boss.proof")}
        </p>
      )}
    </section>
  );
}
