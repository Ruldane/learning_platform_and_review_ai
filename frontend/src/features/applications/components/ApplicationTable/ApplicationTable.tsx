import { useMemo, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { ApplicationView } from "../viewTypes";
import { ApplicationRow } from "./ApplicationRow";
import { SortHeader } from "./SortHeader";
import { nextSort, sortApplications } from "./sort";
import type { SortKey, SortState } from "./sort";

interface ApplicationTableProps {
  applications: ApplicationView[];
  onOpen: (id: string) => void;
}

const COLUMNS: {
  key: SortKey;
  label: "company" | "title" | "status" | "appliedOn" | "nextAction" | "due";
}[] = [
  { key: "company", label: "company" },
  { key: "title", label: "title" },
  { key: "status", label: "status" },
  { key: "appliedOn", label: "appliedOn" },
  { key: "nextActionOn", label: "nextAction" },
  { key: "dueReminders", label: "due" },
];

/** Les candidatures en tableau : six colonnes, tri par clic sur l'en-tête (`aria-sort`). */
export function ApplicationTable({ applications, onOpen }: ApplicationTableProps) {
  const [sort, setSort] = useState<SortState | null>(null);
  const rows = useMemo(() => sortApplications(applications, sort), [applications, sort]);

  if (applications.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("applications.table.empty")}</p>;
  }
  return (
    <div className="overflow-x-auto rounded-xl border bg-card">
      <table className="w-full text-sm">
        <caption className="sr-only">{t("applications.table.label")}</caption>
        <thead className="bg-muted/50">
          <tr>
            {COLUMNS.map(({ key, label }) => (
              <SortHeader
                key={key}
                label={t(`applications.table.${label}`)}
                direction={sort?.key === key ? sort.direction : undefined}
                onSort={() => setSort(nextSort(sort, key))}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((application) => (
            <ApplicationRow key={application.id} application={application} onOpen={onOpen} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
