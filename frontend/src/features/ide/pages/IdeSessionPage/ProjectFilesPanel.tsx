import { useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ProjectTree } from "../../components/ProjectTree";
import type { Workspace } from "../../hooks/useWorkspace";
import type { ProjectCommand } from "../../projectApi";
import { ProjectFileButtons } from "./ProjectFileButtons";
import { ProjectPathForm } from "./ProjectFileForms";
import { ProjectRemoveForm } from "./ProjectRemoveForm";

export function ProjectFilesPanel({ ws }: { ws: Workspace }) {
  const { file, openFile, project, session, tabs } = ws;
  const [mode, setMode] = useState<ProjectCommand["kind"] | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const paths = Object.keys(session.files);
  const busy = project.isPending;
  const reset = () => {
    setMode(null);
    project.reset();
    trigger.current?.focus();
  };
  const submit = (command: ProjectCommand) => project.mutate(command, { onSuccess: reset });
  const form = { path: file, busy, cancel: reset, submit };
  return (
    <section className="grid gap-2 rounded-lg border border-border p-3">
      <h2 className="text-sm font-semibold">{t("ide.project.files")}</h2>
      <ProjectTree
        paths={paths}
        current={file}
        onOpen={(name) => {
          if (!busy && !mode) openFile(name);
        }}
      />
      <ProjectFileButtons
        trigger={trigger}
        busy={busy}
        canRemove={paths.length > 1}
        onChoose={setMode}
      />
      {mode === "create" || mode === "rename" ? (
        <ProjectPathForm key={mode} mode={mode} {...form} />
      ) : null}
      {mode === "remove" ? (
        <ProjectRemoveForm {...form} entry={session.entry} paths={paths} />
      ) : null}
      {project.error ? <InlineError message={errorMessage(project.error)} /> : null}
      {tabs.error ? <InlineError message={errorMessage(tabs.error)} /> : null}
    </section>
  );
}
