import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { DebateFeed, SessionStatusBar } from "@/shared/session-ui";
import { gapKeys } from "../../queryKeys";

const OVER = ["completed", "failed", "cancelled"];

interface AnalysisRunProps {
  sessionId: string;
  postingId: string;
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * Le fil de l'analyse, en direct : état de la session puis bulles de l'Analyste. À la fin de la
 * session, l'offre et l'écart sont relus (la relecture de 3 s fait le reste). Un flux qui
 * abandonne n'affiche rien : la relecture régulière continue de suivre l'analyse.
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
      <SessionStatusBar status={stream.status} cost={stream.view.cost} />
      <DebateFeed items={stream.view.feed} renderInterrupt={() => null} />
    </section>
  );
}
