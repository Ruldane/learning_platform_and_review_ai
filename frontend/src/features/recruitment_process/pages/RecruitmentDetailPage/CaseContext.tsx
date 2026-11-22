import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { Recruitment } from "../../api";

export function CaseContext({ row }: { row: Recruitment }) {
  return (
    <section className="grid gap-3 rounded-xl border bg-card p-4">
      <h2 className="font-semibold">{t("recruitmentProcess.missing")}</h2>
      {row.project ? (
        <p>
          {t("recruitmentProcess.projectSource")} ·{" "}
          <Link className="underline" to={`/competences/portfolio/${row.project.id}`}>{row.project.title}</Link>
        </p>
      ) : <p>{t("recruitmentProcess.noProject")}</p>}
      {row.missing_proofs.length ? (
        <ul className="list-disc space-y-1 pl-5">
          {row.missing_proofs.map((proof) => (
            <li key={proof.requirement}>
              {proof.requirement}
              {proof.skills.length ? <span> · {proof.skills.join(", ")}</span> : null}
            </li>
          ))}
        </ul>
      ) : <p>{t("recruitmentProcess.missingNone")}</p>}
      <h2 className="font-semibold">{t("recruitmentProcess.rubric")}</h2>
      <dl className="grid gap-2 text-sm">
        {row.rubric.map((item) => <div key={item.label}><dt className="font-medium">{item.label}</dt><dd>{item.instructions}</dd></div>)}
      </dl>
    </section>
  );
}
