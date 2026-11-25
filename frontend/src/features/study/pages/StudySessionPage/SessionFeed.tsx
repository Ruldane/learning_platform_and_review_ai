import { t } from "@/shared/i18n/t";
import { DebateFeed, MessageComposer } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import { errorMessage } from "@/shared/api/errors";
import { VoicePlayback } from "@/shared/voice";
import type { StudyRun } from "../../hooks/useStudyRun";
import { TutorInterrupt } from "./TutorInterrupt";

interface SessionFeedProps {
  run: StudyRun;
  /** The agent session is still live: the message field is open. */
  live: boolean;
  finishing: boolean;
}

/** Left column: the exchange with the Tutor (bubbles, questions) and the message field. */
export function SessionFeed({ run, live, finishing }: SessionFeedProps) {
  const { stream, actions } = run;
  const answering = stream.view.pendingInterrupt?.kind === "tutor_question";
  const latest = stream.view.feed.findLast((item) => item.kind === "turn");
  return (
    <section aria-label={t("study.session.feed")} className="flex min-w-0 flex-col gap-3">
      {stream.connection === "reconnecting" ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("study.session.reconnecting")}
        </p>
      ) : null}
      <DebateFeed
        items={stream.view.feed}
        renderInterrupt={(item) => <TutorInterrupt item={item} run={run} />}
      />
      {actions.error ? <InlineError message={actions.error} /> : null}
      {run.finishError ? <InlineError message={errorMessage(run.finishError)} /> : null}
      {!answering && latest?.kind === "turn" && !latest.streaming && (
        <VoicePlayback text={latest.text} />
      )}
      <MessageComposer
        disabled={!live || finishing}
        voice={!answering}
        onSend={(text) => void actions.sendMessage(text)}
      />
    </section>
  );
}
