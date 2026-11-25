import { useEffect, type RefObject } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import type { SessionEvent } from "@/shared/realtime/types";
import { useRun } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { useKitSync } from "../../hooks/useKitSync";

/** Count the kit item artifacts announced by the current run. */
function kitArrivals(events: SessionEvent[]): number {
  return events.filter(
    (event) => event.type === "artifact.ready" && event.payload.kind === "kit_item",
  ).length;
}

interface KitRunProps {
  applicationId: string;
  sessionId: string;
  /** Whether the server reports an active kit run. */
  running: boolean;
  /** The preparation note receives focus after the user starts the kit. */
  noteRef: RefObject<HTMLParagraphElement | null>;
  createSocket?: SocketFactory;
}

/**
 * Follow the run and refresh kit data when a piece arrives or the session status changes.
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
