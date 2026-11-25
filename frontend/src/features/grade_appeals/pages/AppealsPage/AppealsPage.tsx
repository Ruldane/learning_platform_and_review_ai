import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { APPEALS, listAppeals } from "../../api";
import { AppealCreateBox } from "./AppealCreateBox";

export function AppealsPage() {
  const rows = useQuery({ queryKey: APPEALS, queryFn: ({ signal }) => listAppeals(signal) });
  return (
    <section className="grid max-w-3xl gap-5">
      <h1 className="text-2xl font-semibold">{t("gradeAppeals.title")}</h1>
      <AppealCreateBox />
      <h2 className="text-lg font-semibold">{t("gradeAppeals.list")}</h2>
      {rows.isPending ? <LoadingState label={t("gradeAppeals.loading")} /> : null}
      {rows.error ? <ErrorState message={errorMessage(rows.error)} onRetry={() => void rows.refetch()} /> : null}
      {rows.data?.length === 0 ? <p>{t("gradeAppeals.empty")}</p> : null}
      {rows.data?.length ? (
        <ul className="grid gap-3">
          {rows.data.map((row) => (
            <li key={row.id} className="grid gap-2 rounded-xl border bg-card p-4">
              <Link className="font-medium underline" to={`/skills/appeals/${row.id}`}>
                {row.source.project.title} · {row.source.criterion.criterion}
              </Link>
              <p className="text-sm">{t(`gradeAppeals.status.${row.state}`)}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
