import { useEffect, type RefObject } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import type { SessionEvent } from "@/shared/realtime/types";
import { useRun } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { useKitSync } from "../../hooks/useKitSync";

/** Les pièces que la session a rangées : chaque `artifact.ready` de genre `kit_item` (rien pour une pièce en échec). */
export function kitArrivals(events: SessionEvent[]): number {
  return events.filter(
    (event) => event.type === "artifact.ready" && event.payload.kind === "kit_item",
  ).length;
}

interface KitRunProps {
  applicationId: string;
  sessionId: string;
  /** Le serveur dit qu'un kit est en cours. */
  running: boolean;
  /** La note « le kit se prépare » : elle reçoit le focus quand January vient de lancer le kit. */
  noteRef: RefObject<HTMLParagraphElement | null>;
  createSocket?: SocketFactory;
}

/**
 * La session du kit suivie en direct. Le flux ne fait que dire quand relire le kit : à chaque
 * pièce rangée (`artifact.ready`), à chaque changement d'état de la session (dont sa fin) ; l'état
 * des pièces vient toujours de la lecture du kit.
 */
export function KitRun({ applicationId, sessionId, running, noteRef, createSocket }: KitRunProps) {
  const sync = useKitSync(applicationId);
  const run = useRun(sessionId, sync, createSocket);
  const arrivals = kitArrivals(run.stream.events);

  useEffect(() => {
    if (arrivals > 0) sync();
  }, [arrivals, sync]);

  async function cancel() {
    if (await run.actions.cancel()) sync();
  }

  return (
    <section className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      {running ? (
        <p ref={noteRef} tabIndex={-1} className="text-sm font-medium outline-none">
          {t("applications.kitPage.running")}
        </p>
      ) : null}
      <RunFeed run={run} label={t("applications.kitPage.feed")} />
      {run.over ? null : (
        <div>
          <Button type="button" variant="outline" onClick={() => void cancel()}>
            {t("applications.kitPage.cancel")}
          </Button>
        </div>
      )}
    </section>
  );
}
