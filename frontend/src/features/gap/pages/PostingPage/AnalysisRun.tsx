import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { DebateFeed, SessionStatusBar } from "@/shared/session-ui";
import { gapKeys } from "../../queryKeys";

const OVER = ["completed", "failed", "cancelled", "expired"];

interface AnalysisRunProps {
  sessionId: string;
  postingId: string;
  /** Only used by tests (fake WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * The analysis feed, live: session state, then the Analyst's bubbles. At the end of the
 * session, the posting and gap are re-read (the 3 s re-read does the rest). A stream that
 * drops shows nothing: the regular re-read keeps following the analysis.
 */
export function AnalysisRun({ sessionId, postingId, createSocket }: AnalysisRunProps) {
  const client = useQueryClient();
  const stream = useSessionStream(sessionId, { createSocket });
  const over = OVER.includes(stream.status);

  useEffect(() => {
    if (!over) return;
    void client.invalidateQueries({ queryKey: gapKeys.posting(postingId) });
    void client.invalidateQueries({ queryKey: gapKeys.gap(postingId) });
  }, [client, postingId, over]);

  if (stream.connection === "failed") return null;
  return (
    <section aria-label={t("gap.posting.feed")} className="flex flex-col gap-3">
      <SessionStatusBar status={stream.status} cost={stream.view.cost}
        playedBy={stream.view.playedBy} waitingForClient={stream.view.pendingInterrupt?.kind === "mcp_model"} />
      <DebateFeed items={stream.view.feed} renderInterrupt={() => null} />
    </section>
  );
}
