import { useMemo, useRef, useState } from "react";
import { toAnnotations, toNoteViews, toUsageView } from "../toView";
import type { IdeSession } from "../types";
import { useCoach } from "./useCoach";
import { useFilesDraft } from "./useFilesDraft";
import { useIdleTeach } from "./useIdleTeach";
import { useNotes } from "./useNotes";
import { usePreferences } from "./usePreferences";
import { useProposals } from "./useProposals";
import { useRunner } from "./useRunner";
import { useUsage } from "./useUsage";

/**
 * Tout ce que la séance relie : les fichiers, le fichier et la ligne ouverts, l'exécution, le
 * professeur et ses notes. Le professeur ne part que sur un geste : fin d'une exécution en échec
 * (mode automatique ouvert), « Indice », « Pourquoi », une question, ou 30 s d'arrêt si l'option
 * est cochée. Jamais à la frappe.
 */
export function useWorkspace(session: IdeSession) {
  const draft = useFilesDraft(session);
  const [file, setFile] = useState(session.entry);
  const [line, setLine] = useState<number | null>(null);
  const [activity, setActivity] = useState(0);
  const preferences = usePreferences();
  const usage = useUsage(session.id);
  const notes = useNotes(session.id);
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
  const noteViews = useMemo(
    () => toNoteViews(notes.data ?? [], draft.files),
    [notes.data, draft.files],
  );
  const annotations = useMemo(() => toAnnotations(noteViews, file), [noteViews, file]);
  return {
    session,
    draft,
    file,
    openFile: setFile,
    setLine,
    typed: () => setActivity((count) => count + 1),
    preferences,
    usage: usage.data ? toUsageView(usage.data) : null,
    coach,
    runner,
    proposals,
    notes: noteViews,
    annotations,
    panelHeading,
  };
}

export type Workspace = ReturnType<typeof useWorkspace>;
