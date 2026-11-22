import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { NotebookCell } from "../../notebookApi";

interface Props {
  cell: NotebookCell;
  number: number;
  busy: boolean;
  edit: (source: string) => void;
  run: () => void;
  remove: () => void;
}

export function NotebookCellEditor({ cell, number, busy, edit, run, remove }: Props) {
  const label = { number };
  return (
    <li className="grid gap-2 rounded-md border border-border p-2">
      <label className="grid gap-1 text-sm">
        {t("ide.notebook.source", label)} · {t(`ide.notebook.kind.${cell.kind}`)}
        <textarea
          aria-label={t("ide.notebook.source", label)}
          value={cell.source}
          readOnly={busy}
          onChange={(event) => edit(event.target.value)}
          rows={4}
          className="rounded border border-border bg-background p-1.5 font-mono focus-visible:ring-2 focus-visible:ring-ring"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        {cell.kind === "code" ? (
          <Button type="button" size="sm" disabled={busy} onClick={run}>
            {t("ide.notebook.run", label)}
          </Button>
        ) : null}
        <Button type="button" size="sm" variant="outline" disabled={busy} onClick={remove}>
          {t("ide.notebook.remove", label)}
        </Button>
      </div>
      {cell.output !== null && cell.output !== undefined ? (
        <pre className="max-h-40 overflow-auto rounded bg-muted p-2 text-sm" tabIndex={0}>
          {cell.output}
        </pre>
      ) : null}
    </li>
  );
}
