import { t } from "@/shared/i18n/t";
import { ClaudeChanges } from "../../components/ClaudeChanges";
import { OutputPanel } from "../../components/OutputPanel";
import type { Workspace } from "../../hooks/useWorkspace";
import { FileTabs } from "./FileTabs";
import { ProjectFilesPanel } from "./ProjectFilesPanel";
import { SessionFileEditor } from "./SessionFileEditor";
import { SessionToolbar } from "./SessionToolbar";

/** On the left: the files, the editor, the run buttons and the output. */
export function EditorColumn({ ws }: { ws: Workspace }) {
  const { draft, runner, file, session } = ws;
  const { claude } = draft;
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
      <ProjectFilesPanel ws={ws} />
      <FileTabs
        names={ws.tabs.paths}
        current={file}
        entry={session.entry}
        changed={claude.notices}
        onOpen={ws.project.isPending ? () => undefined : ws.openFile}
        onClose={session.tabs && !ws.project.isPending ? ws.tabs.closeFile : undefined}
      />
      <ClaudeChanges
        file={file}
        notices={claude.notices}
        conflicts={claude.conflicts}
        onDismiss={claude.dismiss}
        onKeepMine={claude.keepMine}
        onTakeTheirs={claude.takeTheirs}
      />
      <SessionFileEditor ws={ws} />
      <OutputPanel view={runner.output} />
    </div>
  );
}
