import { t } from "@/shared/i18n/t";
import { isAwaitingAnswer } from "@/shared/realtime/feedHelpers";
import { DebateFeed, InterruptCard, MessageComposer } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { ReplanRun } from "../../hooks/useReplanRun";

/**
 * The replan thread: Strategist bubbles and question cards (`replan_option`,
 * `accept_replan`). An answer goes out by resuming the session; the message field stays
 * open while the session lives. On `accept_replan`, the button clicked decides even with a note
 * (`{ action, note }`); « Répondre » alone asks for another proposal.
 */
const withNote = (action: string, answers: Record<string, string>) => ({
  action,
  note: answers.note ?? "",
});

export function ReplanFeed({ run }: { run: ReplanRun }) {
  const { stream, actions, over } = run;
  return (
    <div className="flex flex-col gap-3">
      {stream.connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("replan.run.reconnecting")}
        </p>
      ) : null}
      <DebateFeed
        items={stream.view.feed}
        renderInterrupt={({ interrupt, answered }) => (
          <InterruptCard
            interrupt={interrupt}
            answered={answered}
            disabled={actions.pending || !isAwaitingAnswer(stream.view, interrupt.interrupt_id)}
            onAnswer={(value) => void actions.resume(interrupt.interrupt_id, value)}
            optionWithAnswers={interrupt.kind === "accept_replan" ? withNote : undefined}
          />
        )}
      />
      {actions.error ? <InlineError message={actions.error} /> : null}
      <MessageComposer disabled={over} onSend={(text) => void actions.sendMessage(text)} />
    </div>
  );
}
