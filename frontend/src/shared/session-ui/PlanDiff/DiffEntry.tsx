import { t } from "@/shared/i18n/t";

interface DiffEntryProps {
  title: string;
  moduleTitle: string;
  detail?: string | null;
}

/** A diff task: its title, its module (omitted if unknown), and its change (day or move). */
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
