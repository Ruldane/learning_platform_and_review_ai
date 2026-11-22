import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useSend, useTurnStream } from "../../hooks/useConversation";
import { sendTrainingQuestion, type TrainingChange, type TrainingSession } from "../../trainingApi";
import { ConversationComposer } from "../LessonConversation/ConversationComposer";
import { ConversationTranscript } from "../LessonConversation/ConversationTranscript";
import { TrainingControls } from "./TrainingControls";

interface TrainingRunningProps {
  session: TrainingSession;
  sessionId: string | null;
  saving: boolean;
  initialText: string;
  onChange: (body: TrainingChange) => void;
  onSubmitted: (id: string) => void;
  onRefresh: () => void;
}

export function TrainingRunning({
  session,
  sessionId,
  saving,
  initialText,
  onChange,
  onSubmitted,
  onRefresh,
}: TrainingRunningProps) {
  const send = useSend(
    (message, choice) => sendTrainingQuestion(session.id, message, choice),
    onSubmitted,
  );
  const streaming = useTurnStream(sessionId, "training_tutor", onRefresh);
  const busy = send.pending || sessionId !== null;
  return (
    <section className="flex max-w-3xl flex-col gap-3">
      <TrainingControls mode={session.mode} saving={saving} busy={busy} onChange={onChange} />
      <div className="flex h-[min(44rem,72dvh)] min-h-[24rem] flex-col rounded-xl border border-border">
        <ConversationTranscript
          turns={session.conversation.turns}
          sessionId={sessionId}
          streaming={streaming}
          assistant={t("training.tutor")}
          label={t("training.thread")}
          typing={t("training.typing")}
          greeting={session.greeting}
        />
        {send.error ? <InlineError message={errorMessage(send.error)} /> : null}
        <ConversationComposer
          identity={session.id}
          label={t("training.message")}
          placeholder={t("training.placeholder")}
          initialText={initialText}
          busy={busy || saving}
          usage={session.conversation.usage}
          onSend={send.send}
        />
      </div>
    </section>
  );
}
