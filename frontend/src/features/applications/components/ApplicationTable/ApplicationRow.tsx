import { t } from "@/shared/i18n/t";
import { formatDay } from "../format";
import { describeNextAction } from "../nextAction";
import { OpenApplicationButton } from "../OpenApplicationButton";
import { StatusBadge } from "../StatusBadge";
import type { ApplicationView } from "../viewTypes";

interface ApplicationRowProps {
  application: ApplicationView;
  onOpen: (id: string) => void;
}

/** Une ligne du tableau : l'entreprise ouvre la fiche. */
export function ApplicationRow({ application, onOpen }: ApplicationRowProps) {
  const { title, company, appliedOn, dueReminders } = application;
  return (
    <tr className="border-t">
      <td className="px-3 py-2 font-medium">
        <OpenApplicationButton application={application} onOpen={onOpen}>
          {company}
        </OpenApplicationButton>
      </td>
      <td className="px-3 py-2">{title}</td>
      <td className="px-3 py-2">
        <StatusBadge status={application.status} />
      </td>
      <td className="px-3 py-2 tabular-nums">
        {appliedOn ? formatDay(appliedOn) : t("applications.table.none")}
      </td>
      <td className="px-3 py-2">
        {describeNextAction(application) ?? t("applications.table.none")}
      </td>
      <td className="px-3 py-2 tabular-nums">{dueReminders}</td>
    </tr>
  );
}
