import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { RunLog } from "../../components/RunLog";
import { useNotebook } from "../../hooks/useNotebook";
import type { NotebookDrafts } from "../../hooks/useNotebookDrafts";
import { NotebookCellEditor } from "./NotebookCellEditor";
import { NotebookToolbar } from "./NotebookToolbar";

interface NotebookPanelProps {
  sessionId: string;
  path: string;
  drafts: NotebookDrafts;
}

export function NotebookPanel({ sessionId, path, drafts }: NotebookPanelProps) {
  const nb = useNotebook(sessionId, path, drafts);
  const [replay, setReplay] = useState(false);
  if (nb.query.isPending) return <LoadingState label={t("ide.notebook.loading")} />;
  if (nb.query.isError)
    return (
      <InlineError message={errorMessage(nb.query.error)} onRetry={() => void nb.query.refetch()} />
    );
  const busy = nb.pending || nb.progress?.status === "running";
  function add(kind: "code" | "markdown") {
    nb.setDraft([...nb.cells, { id: crypto.randomUUID(), kind, source: "" }]);
  }
  const edit = (id: string, source: string) =>
    nb.setDraft(
      nb.cells.map((item) => (item.id === id ? { ...item, source, output: null } : item)),
    );
  return (
    <section
      aria-label={t("ide.notebook.title")}
      className="grid gap-3 rounded-lg border border-border p-3"
    >
      <NotebookToolbar
        busy={busy}
        canAdd={nb.cells.length < 100}
        dirty={nb.dirty}
        replay={replay}
        add={add}
        save={() => nb.action.mutate(null)}
        setReplay={setReplay}
      />
      <ol className="grid gap-2">
        {nb.cells.map((cell, index) => (
          <NotebookCellEditor
            key={cell.id}
            cell={cell}
            number={index + 1}
            busy={busy}
            edit={(source) => edit(cell.id, source)}
            run={() => nb.action.mutate({ cellId: cell.id, includePrevious: replay })}
            remove={() => nb.setDraft(nb.cells.filter((item) => item.id !== cell.id))}
          />
        ))}
      </ol>
      {nb.progress ? <RunLog label={t("ide.notebook.output")} output={nb.progress.output} /> : null}
      {nb.action.error ? <InlineError message={errorMessage(nb.action.error)} /> : null}
      {nb.progress?.error ? <InlineError message={nb.progress.error} /> : null}
    </section>
  );
}
