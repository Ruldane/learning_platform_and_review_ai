import { useQueryClient } from "@tanstack/react-query";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ideKeys } from "../../queryKeys";

interface TeacherActivityProps {
  /** La séance de code (pour relire ses notes et sa consommation). */
  ideSessionId: string;
  /** La session d'agents du professeur, rendue par `POST /teach`. */
  teacherSessionId: string;
  createSocket?: SocketFactory;
}

/**
 * Le professeur travaille : le texte le dit tant que sa session tourne. À chaque changement
 * d'état, les notes et la consommation sont relues, si bien que sa réponse apparaît dans la liste
 * sans rien à faire.
 */
export function TeacherActivity({
  ideSessionId,
  teacherSessionId,
  createSocket,
}: TeacherActivityProps) {
  const queryClient = useQueryClient();
  const reload = () => {
    void queryClient.invalidateQueries({ queryKey: ideKeys.notes(ideSessionId) });
    void queryClient.invalidateQueries({ queryKey: ideKeys.usage(ideSessionId) });
  };
  const run = useRun(teacherSessionId, reload, createSocket);
  const status = run.stream.status;
  if (status === "failed" || status === "cancelled") {
    return <InlineError message={run.stream.view.error?.message ?? t("ide.teacher.failed")} />;
  }
  return (
    <p role="status" className="text-sm text-muted-foreground">
      {run.over ? null : t("ide.teacher.thinking")}
    </p>
  );
}
