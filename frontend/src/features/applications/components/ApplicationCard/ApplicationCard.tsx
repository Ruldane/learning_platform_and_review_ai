import { t } from "@/shared/i18n/t";
import { formatDay } from "../format";
import { describeNextAction } from "../nextAction";
import { OpenApplicationButton } from "../OpenApplicationButton";
import { StatusBadge } from "../StatusBadge";
import type { ApplicationView } from "../viewTypes";

interface ApplicationCardProps {
  application: ApplicationView;
  /** False in a tracking table column, where the status is the column's. */
  showStatus?: boolean;
  onOpen?: (id: string) => void;
}

/** The content of a record on a card: company, role, date, next action, reminders due. */
export function ApplicationCard({ application, showStatus = false, onOpen }: ApplicationCardProps) {
  const { company, title, appliedOn, dueReminders } = application;
  const action = application.nextAction ? describeNextAction(application) : null;
  const name = (
    <>
      <span className="block font-medium break-words">{company}</span>
      <span className="block break-words text-muted-foreground">{title}</span>
    </>
  );
  return (
    <div className="flex min-w-0 flex-col gap-1 text-sm">
      {onOpen ? (
        <OpenApplicationButton application={application} onOpen={onOpen}>
          {name}
        </OpenApplicationButton>
      ) : (
        <div>{name}</div>
      )}
      {showStatus && <StatusBadge status={application.status} className="self-start" />}
      <p className="text-xs text-muted-foreground">
        {appliedOn
          ? t("applications.card.appliedOn", { date: formatDay(appliedOn) })
          : t("applications.card.notApplied")}
      </p>
      {action && (
        <p className="text-xs break-words">{t("applications.card.nextAction", { action })}</p>
      )}
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
