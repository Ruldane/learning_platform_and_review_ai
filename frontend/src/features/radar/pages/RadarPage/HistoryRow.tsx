import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { fullDateTime } from "@/shared/lib/relativeTime";
import { failureReason } from "../../errors";
import type { HistoryItemView } from "../../toView";

/** Une ligne de l'historique : date (lien), état écrit, poste et zone, décompte ou raison de l'échec. */
export function HistoryRow({ item, current }: { item: HistoryItemView; current: boolean }) {
  const when = fullDateTime(item.createdAt);
  return (
    <li
      aria-current={current ? "true" : undefined}
      className={`flex flex-col gap-1 rounded-xl border bg-card p-3 text-sm ${current ? "border-primary" : ""}`}
    >
      <span className="flex flex-wrap items-baseline gap-x-3">
        <Link to={`/carriere/radar/${item.id}`} className="font-medium underline">
          {when}
        </Link>
        <span className="font-medium">{t(`radar.history.status.${item.status}`)}</span>
        <span className="text-muted-foreground">{t(`radar.history.trigger.${item.trigger}`)}</span>
        {current ? (
          <span className="text-muted-foreground">{t("radar.history.current")}</span>
        ) : null}
      </span>
      <span className="text-muted-foreground">
        {t("radar.history.scope", { role: item.role, zone: item.zone })}
      </span>
      {item.status === "failed" ? (
        <span>{t("radar.failure.reason", { reason: failureReason(item.errorCode) })}</span>
      ) : (
        <span className="tabular-nums">
          {t("radar.history.counts", {
            read: item.readCount,
            blocked: item.blockedCount,
            analyzed: item.analyzed,
          })}
          {item.lowSample ? ` · ${t("radar.history.lowSample")}` : ""}
        </span>
      )}
    </li>
  );
}
