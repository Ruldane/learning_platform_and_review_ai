import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { readHistory, type RoutineAction } from "../../api";
import { CommitmentNotices } from "../../components/CommitmentNotices";
import { ROUTINES } from "../../queryKeys";

const timeLabel = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

export function History({ id, action }: { id: string; action: RoutineAction }) {
  const history = useQuery({
    queryKey: [...ROUTINES, "history", id],
    queryFn: () => readHistory(id),
    refetchInterval: 5000,
  });
  return (
    <section className="space-y-2" aria-labelledby="routines-history">
      <h2 id="routines-history" className="text-lg font-semibold">
        {t("routines.history")}
      </h2>
      {history.error ? <InlineError message={errorMessage(history.error)} /> : null}
      {history.data?.length === 0 ? <p>{t("routines.empty")}</p> : null}
      <ul className="space-y-2">
        {history.data?.map((execution) => (
          <li key={execution.id} className="rounded-md border p-3">
            <p>{t(`routines.counts.${action}`, { count: execution.result_count })}</p>
            <span>
              {t(execution.source === "scheduled" ? "routines.scheduled" : "routines.manual")}
            </span>
            {" · "}
            <time dateTime={execution.created_at}>
              {timeLabel.format(new Date(execution.created_at))}
            </time>
            <CommitmentNotices notices={execution.notices} />
          </li>
        ))}
      </ul>
    </section>
  );
}
