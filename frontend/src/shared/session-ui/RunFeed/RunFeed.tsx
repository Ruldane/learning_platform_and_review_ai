import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { isAwaitingAnswer } from "@/shared/realtime/feedHelpers";
import type { FeedItem } from "@/shared/realtime/types";
import type { Run } from "@/shared/realtime/useRun";
import { InlineError } from "@/shared/ui/states/InlineError";
import { DebateFeed } from "../DebateFeed";
import { InterruptCard } from "../InterruptCard";
import { SessionStatusBar } from "../SessionStatusBar";

export type InterruptItem = Extract<FeedItem, { kind: "interrupt" }>;

interface RunFeedProps {
  run: Run;
  label: string;
  /** A card specific to one question; `undefined` keeps the common card. */
  renderInterrupt?: (item: InterruptItem) => ReactNode | undefined;
}

/** Is the question still open, and is the page free to answer it? */
export const canAnswer = (run: Run, item: InterruptItem): boolean =>
  isAwaitingAnswer(run.stream.view, item.interrupt.interrupt_id) && !run.actions.pending;

/** Feed of a session followed by `useRun` (CV, applications); the common card is the fallback. */
export function RunFeed({ run, label, renderInterrupt }: RunFeedProps) {
  const { stream, actions } = run;
  const common = (item: InterruptItem) => (
    <InterruptCard
      interrupt={item.interrupt}
      answered={item.answered}
      disabled={!canAnswer(run, item)}
      onAnswer={(value) => void actions.resume(item.interrupt.interrupt_id, value)}
    />
  );
  return (
    <section aria-label={label} className="flex min-w-0 flex-col gap-3">
      <SessionStatusBar status={stream.status} cost={stream.view.cost}
        playedBy={stream.view.playedBy} waitingForClient={stream.view.pendingInterrupt?.kind === "mcp_model"} />
      {stream.connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("session.reconnecting")}
        </p>
      ) : null}
      <DebateFeed
        items={stream.view.feed}
        renderInterrupt={(item) => {
          const custom = renderInterrupt?.(item);
          return custom === undefined ? common(item) : custom;
        }}
      />
      {actions.error ? <InlineError message={actions.error} /> : null}
    </section>
  );
}
