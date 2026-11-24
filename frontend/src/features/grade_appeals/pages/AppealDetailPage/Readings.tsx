import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { Appeal } from "../../api";

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "long" });

export function Readings({ row }: { row: Appeal }) {
  const original = row.source.criterion;
  return (
    <>
      <p><Link className="underline" to={`/competences/portfolio/${row.source.project.id}`}>{row.source.project.title}</Link></p>
      <details className="rounded-xl border bg-card p-4">
        <summary>{t("gradeAppeals.snapshot")}</summary>
        <time dateTime={row.source.submitted_at} className="text-sm text-muted-foreground">
          {dateFormat.format(new Date(row.source.submitted_at))}
        </time>
        <p className="whitespace-pre-wrap">{row.source.submission}</p>
      </details>
      <div className="grid gap-1">
        <h2 className="font-semibold">{t("gradeAppeals.reason")}</h2>
        <p className="whitespace-pre-wrap">{row.reason}</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <article className="grid gap-2 rounded-xl border bg-card p-4">
          <h2 className="font-semibold">{t("gradeAppeals.original")}</h2>
          <p className="font-medium">{t(original.original_met ? "gradeAppeals.met" : "gradeAppeals.missed")}</p>
          <p className="whitespace-pre-wrap">{original.original_comment}</p>
        </article>
        {row.second ? (
          <article className="grid gap-2 rounded-xl border bg-card p-4">
            <h2 className="font-semibold">{t("gradeAppeals.second")}</h2>
            <p className="font-medium">{t(row.second.met ? "gradeAppeals.met" : "gradeAppeals.missed")}</p>
            <p className="whitespace-pre-wrap">{row.second.comment}</p>
          </article>
        ) : null}
      </div>
    </>
  );
}
