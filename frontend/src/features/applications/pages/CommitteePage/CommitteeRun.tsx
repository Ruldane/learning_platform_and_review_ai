import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { applicationsKeys } from "../../queryKeys";
import type { CommitteeView } from "../../types";
import { CommitteeSide } from "./CommitteeSide";

interface CommitteeRunProps {
  view: CommitteeView;
  createSocket?: SocketFactory;
}

/**
 * Le Conseil du comité (SPEC 15.2) : le débat à gauche (40 %), les votes, le verdict et l'avant /
 * après à droite (60 %). Le fil ne fait que dire quand relire l'exécution (chaque changement d'état
 * de la session) ; les résultats viennent toujours de la lecture.
 */
export function CommitteeRun({ view, createSocket }: CommitteeRunProps) {
  const client = useQueryClient();
  const sync = useCallback(() => {
    void client.invalidateQueries({ queryKey: applicationsKeys.committee(view.id) });
    void client.invalidateQueries({ queryKey: applicationsKeys.committees(view.postingId) });
  }, [client, view.id, view.postingId]);
  const run = useRun(view.sessionId, sync, createSocket);

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[2fr_3fr]">
      <RunFeed run={run} label={t("applications.committeePage.feed")} />
      <CommitteeSide view={view} />
    </div>
  );
}
