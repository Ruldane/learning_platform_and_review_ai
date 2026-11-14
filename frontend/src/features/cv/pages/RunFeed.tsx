import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { isAwaitingAnswer } from "@/shared/realtime/feedHelpers";
import type { FeedItem } from "@/shared/realtime/types";
import { DebateFeed, InterruptCard, SessionStatusBar } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { Run } from "../hooks/useRun";

export type InterruptItem = Extract<FeedItem, { kind: "interrupt" }>;

interface RunFeedProps {
  run: Run;
  label: string;
  /** Une carte propre à une question ; `undefined` laisse la carte commune. */
  renderInterrupt?: (item: InterruptItem) => ReactNode | undefined;
}

/** La question est-elle encore ouverte et la page libre d'y répondre ? */
export const canAnswer = (run: Run, item: InterruptItem): boolean =>
  isAwaitingAnswer(run.stream.view, item.interrupt.interrupt_id) && !run.actions.pending;

/** Le fil d'une session du CV : état, bulles des agents, questions ; la carte commune sert de repli. */
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
      <SessionStatusBar status={stream.status} cost={stream.view.cost} />
      {stream.connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("cv.templatePage.reconnecting")}
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
