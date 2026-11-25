import { useMemo, useRef, useState } from "react";
import { toAnnotations, toNoteViews, toUsageView } from "../toView";
import type { IdeSession } from "../types";
import { useCoach } from "./useCoach";
import { useFilesDraft } from "./useFilesDraft";
import { useIdleTeach } from "./useIdleTeach";
import type { Files } from "./fileMaps";
import { useNotebookDrafts } from "./useNotebookDrafts";
import { useNotes } from "./useNotes";
import { usePreferences } from "./usePreferences";
import { useProjectFiles } from "./useProjectFiles";
import { useProjectTabs } from "./useProjectTabs";
import { useProposals } from "./useProposals";
import { useRunner } from "./useRunner";
import { useUsage } from "./useUsage";

function useNoteViews(sessionId: string, files: Files, file: string) {
  const notes = useNotes(sessionId);
  const views = useMemo(() => toNoteViews(notes.data ?? [], files), [notes.data, files]);
  const annotations = useMemo(() => toAnnotations(views, file), [views, file]);
  return { notes: views, annotations };
}

/**
 * Everything the session links: the files, the open file and line, the run, the
 * teacher and its notes. The teacher only fires on an action: end of a failed run
 * (automatic mode on), « Indice », « Pourquoi », a question, or 30 s idle if the option
 * is checked. Never on typing.
 */
export function useWorkspace(session: IdeSession) {
  const draft = useFilesDraft(session);
  const notebookDrafts = useNotebookDrafts();
  const tabs = useProjectTabs(session);
  const { file } = tabs;
  const project = useProjectFiles(session, draft.save, (updated, command) => {
    draft.discard();
    if (command.kind === "create") tabs.openFile(command.path, updated);
    else tabs.follow(updated);
  });
  const [line, setLine] = useState<number | null>(null);
  const [activity, setActivity] = useState(0);
  const preferences = usePreferences();
  const usage = useUsage(session.id);
  const noteViews = useNoteViews(session.id, draft.files, file);
  const panelHeading = useRef<HTMLHeadingElement>(null);
  const onDemand = usage.data?.mode_on_demand ?? true;
  const automatic = preferences.data?.teacher_mode === "auto" && !onDemand;
  const coach = useCoach(session.id, automatic, { filePath: file, line });
  const runner = useRunner(session.id, draft.save, coach.afterRun);
  const proposals = useProposals(session.id, draft, () => panelHeading.current?.focus());
  useIdleTeach({
    enabled: automatic && preferences.data?.idle_trigger === true,
    line,
    activity,
    onIdle: () => coach.ask({ trigger: "idle" }),
  });
  return {
    session,
    draft,
    notebookDrafts,
    file,
    openFile: tabs.openFile,
    tabs,
    project,
    setLine,
    typed: () => setActivity((count) => count + 1),
    preferences,
    usage: usage.data ? toUsageView(usage.data) : null,
    coach,
    runner,
    proposals,
    ...noteViews,
    panelHeading,
  };
}

export type Workspace = ReturnType<typeof useWorkspace>;
