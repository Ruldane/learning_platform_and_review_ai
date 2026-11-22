import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { useSend } from "../../hooks/useConversation";
import type { TrainingSession } from "../../trainingApi";
import { ConversationComposer } from "../LessonConversation/ConversationComposer";
import { ConversationTranscript } from "../LessonConversation/ConversationTranscript";

interface Props {
  session: TrainingSession;
  sessionId: string | null;
  streaming: string | null;
  initialText: string;
  busy: boolean;
  error: unknown;
  onSend: ReturnType<typeof useSend>["send"];
}

export function TrainingConversation({
  session,
  sessionId,
  streaming,
  initialText,
  busy,
  error,
  onSend,
}: Props) {
  return (
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
      {error ? <InlineError message={errorMessage(error)} /> : null}
      <ConversationComposer
        identity={session.id}
        label={t("training.message")}
        placeholder={t("training.placeholder")}
        initialText={initialText}
        busy={busy}
        usage={session.conversation.usage}
        onSend={onSend}
      />
    </div>
  );
}
