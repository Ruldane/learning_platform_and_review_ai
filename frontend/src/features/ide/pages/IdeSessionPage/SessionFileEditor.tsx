import { CodeEditor } from "../../components/CodeEditor";
import type { Workspace } from "../../hooks/useWorkspace";
import { NotebookPanel } from "./NotebookPanel";

export function SessionFileEditor({ ws }: { ws: Workspace }) {
  const { draft, file, session, runner } = ws;
  if (file.toLowerCase().endsWith(".ipynb")) {
    return (
      <NotebookPanel key={file} sessionId={session.id} path={file} drafts={ws.notebookDrafts} />
    );
  }
  return (
    <CodeEditor
      path={file}
      value={draft.files[file] ?? ""}
      readOnly={ws.project.isPending}
      annotations={ws.annotations}
      onChange={(text) => {
        if (ws.project.isPending) return;
        draft.edit(file, text);
        ws.typed();
      }}
      onCursorLine={ws.setLine}
      onRun={() => void runner.start("run")}
    />
  );
}
