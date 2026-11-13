import { t } from "@/shared/i18n/t";

interface DiffEntryProps {
  title: string;
  moduleTitle: string;
  detail?: string | null;
}

/** Une tâche du diff : son titre, son module (omis s'il est inconnu) et ce qui la concerne (jour ou déplacement). */
export function DiffEntry({ title, moduleTitle, detail }: DiffEntryProps) {
  return (
    <li className="flex flex-col gap-0.5">
      <span className="font-medium">{title}</span>
      {moduleTitle === "" ? null : (
        <span className="text-sm text-muted-foreground">
          {t("session.diff.module", { module: moduleTitle })}
        </span>
      )}
      {detail ? <span className="text-sm tabular-nums">{detail}</span> : null}
    </li>
  );
}
