import { t } from "@/shared/i18n/t";
import { CodeEditor } from "../../components/CodeEditor";
import { OutputPanel } from "../../components/OutputPanel";
import type { Workspace } from "../../hooks/useWorkspace";
import { FileTabs } from "./FileTabs";
import { SessionToolbar } from "./SessionToolbar";

/** À gauche : les fichiers, l'éditeur, les boutons d'exécution et la sortie. */
export function EditorColumn({ ws }: { ws: Workspace }) {
  const { draft, runner, file, session } = ws;
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <h2 className="sr-only">{t("ide.session.editor")}</h2>
      <SessionToolbar
        running={runner.running}
        dirty={draft.dirty}
        saving={draft.saving}
        saveError={draft.error}
        runError={runner.startError}
        onRun={() => void runner.start("run")}
        onCheck={() => void runner.start("check")}
      />
      <FileTabs
        names={Object.keys(draft.files)}
        current={file}
        entry={session.entry}
        onOpen={ws.openFile}
      />
      <CodeEditor
        path={file}
        value={draft.files[file] ?? ""}
        annotations={ws.annotations}
        onChange={(text) => {
          draft.edit(file, text);
          ws.typed();
        }}
        onCursorLine={ws.setLine}
        onRun={() => void runner.start("run")}
      />
      <OutputPanel view={runner.output} />
    </div>
  );
}
