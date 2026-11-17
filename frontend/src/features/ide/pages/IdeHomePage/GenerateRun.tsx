import { useQueryClient } from "@tanstack/react-query";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ideKeys } from "../../queryKeys";

interface GenerateRunProps {
  sessionId: string;
  createSocket?: SocketFactory;
}

/**
 * L'écriture d'un exercice par les agents, en direct. À chaque changement d'état la liste des
 * exercices est relue : l'exercice y apparaît dès que la session a fini.
 */
export function GenerateRun({ sessionId, createSocket }: GenerateRunProps) {
  const queryClient = useQueryClient();
  const reload = () => void queryClient.invalidateQueries({ queryKey: ideKeys.exercises });
  const run = useRun(sessionId, reload, createSocket);
  const status = run.stream.status;
  const failed = status === "failed" || status === "cancelled";
  return (
    <div className="flex flex-col gap-2">
      <p role="status" className="text-sm">
        {status === "completed" ? t("ide.form.generated") : null}
        {!run.over ? t("ide.form.generating") : null}
      </p>
      <RunFeed run={run} label={t("ide.form.generateFeed")} />
      {failed ? (
        <InlineError message={run.stream.view.error?.message ?? t("ide.form.generateFailed")} />
      ) : null}
    </div>
  );
}
