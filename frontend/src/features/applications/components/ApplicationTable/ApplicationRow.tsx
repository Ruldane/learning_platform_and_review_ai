import { t } from "@/shared/i18n/t";
import { formatDay } from "../format";
import { StatusBadge } from "../StatusBadge";
import type { ApplicationView } from "../viewTypes";

interface ApplicationRowProps {
  application: ApplicationView;
  onOpen: (id: string) => void;
}

function nextAction({ nextAction: action, nextActionOn: day }: ApplicationView): string {
  if (action && day) return `${action} (${formatDay(day)})`;
  if (action) return action;
  return day ? formatDay(day) : t("applications.table.none");
}

/** Une ligne du tableau : l'entreprise ouvre la fiche. */
export function ApplicationRow({ application, onOpen }: ApplicationRowProps) {
  const { id, company, title, appliedOn, dueReminders } = application;
  return (
    <tr className="border-t">
      <td className="px-3 py-2 font-medium">
        <button
          type="button"
          aria-label={t("applications.card.open", { company, title })}
          onClick={() => onOpen(id)}
          className="rounded text-left outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring"
        >
          {company}
        </button>
      </td>
      <td className="px-3 py-2">{title}</td>
      <td className="px-3 py-2">
        <StatusBadge status={application.status} />
      </td>
      <td className="px-3 py-2 tabular-nums">
        {appliedOn ? formatDay(appliedOn) : t("applications.table.none")}
      </td>
      <td className="px-3 py-2">{nextAction(application)}</td>
      <td className="px-3 py-2 tabular-nums">{dueReminders}</td>
    </tr>
  );
}
