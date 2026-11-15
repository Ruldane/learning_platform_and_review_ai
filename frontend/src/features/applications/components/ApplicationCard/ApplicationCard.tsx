import { t } from "@/shared/i18n/t";
import { formatDay } from "../format";
import { StatusBadge } from "../StatusBadge";
import type { ApplicationView } from "../viewTypes";

interface ApplicationCardProps {
  application: ApplicationView;
  /** Faux dans une colonne de tableau de suivi, où le statut est celui de la colonne. */
  showStatus?: boolean;
  onOpen?: (id: string) => void;
}

function nextAction(application: ApplicationView): string | null {
  const { nextAction: action, nextActionOn: day } = application;
  if (!action) return null;
  return day
    ? t("applications.card.nextActionOn", { action, date: formatDay(day) })
    : t("applications.card.nextActionOnly", { action });
}

/** Le contenu d'une fiche sur une carte : entreprise, poste, date, prochaine action, relances dues. */
export function ApplicationCard({ application, showStatus = false, onOpen }: ApplicationCardProps) {
  const { id, company, title, appliedOn, dueReminders } = application;
  const action = nextAction(application);
  const name = (
    <>
      <span className="block font-medium break-words">{company}</span>
      <span className="block break-words text-muted-foreground">{title}</span>
    </>
  );
  return (
    <div className="flex min-w-0 flex-col gap-1 text-sm">
      {onOpen ? (
        <button
          type="button"
          aria-label={t("applications.card.open", { company, title })}
          onClick={() => onOpen(id)}
          className="rounded text-left outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring"
        >
          {name}
        </button>
      ) : (
        <div>{name}</div>
      )}
      {showStatus && <StatusBadge status={application.status} className="self-start" />}
      <p className="text-xs text-muted-foreground">
        {appliedOn
          ? t("applications.card.appliedOn", { date: formatDay(appliedOn) })
          : t("applications.card.notApplied")}
      </p>
      {action && <p className="text-xs break-words">{action}</p>}
      {dueReminders > 0 && (
        <p className="text-xs font-medium text-destructive">
          {dueReminders === 1
            ? t("applications.card.due.one")
            : t("applications.card.due.many", { count: dueReminders })}
        </p>
      )}
    </div>
  );
}
