import { t } from "@/shared/i18n/t";

interface DiffEntryProps {
  title: string;
  moduleTitle: string;
  detail: string;
}

/** Une tâche du diff : son titre, son module et ce qui la concerne (jour prévu ou déplacement). */
export function DiffEntry({ title, moduleTitle, detail }: DiffEntryProps) {
  return (
    <li className="flex flex-col gap-0.5">
      <span className="font-medium">{title}</span>
      <span className="text-sm text-muted-foreground">
        {t("program.diff.module", { module: moduleTitle })}
      </span>
      <span className="text-sm tabular-nums">{detail}</span>
    </li>
  );
}
