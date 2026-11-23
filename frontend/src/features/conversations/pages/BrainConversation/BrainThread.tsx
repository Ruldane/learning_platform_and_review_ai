import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { fetchBrainConversation, sendBrainQuestion } from "../../api";
import { useThread } from "../../hooks/useConversation";
import { threadKey } from "../../hooks/useConversationList";
import { ConversationComposer } from "../LessonConversation/ConversationComposer";
import { ConversationTranscript } from "../LessonConversation/ConversationTranscript";

export function BrainThread({ id, onSubmitted }: { id: string | null; onSubmitted: () => void }) {
  const { thread, sessionId, streaming, sending } = useThread({
    key: threadKey("brain", id ?? undefined),
    read: (signal) => fetchBrainConversation(id, signal),
    submit: (message, source) => sendBrainQuestion(id, message, source),
    agent: "brain_librarian",
    onSubmitted,
  });
  return (
    <div className="flex min-w-0 max-w-3xl flex-col gap-3">
      <div className="flex h-[min(44rem,72dvh)] min-h-[24rem] flex-col rounded-xl border border-border">
        {thread.isPending ? <LoadingState label={t("conversations.loading")} /> : null}
        {thread.isError ? (
          <InlineError message={errorMessage(thread.error)} onRetry={() => void thread.refetch()} />
        ) : null}
        {!thread.isPending && !thread.isError ? (
          <ConversationTranscript
            turns={thread.data?.turns ?? []}
            sessionId={sessionId}
            streaming={streaming}
            assistant={t("brain.chat.librarian")}
            label={t("brain.chat.thread")}
            emptyText={t("brain.chat.empty")}
            typing={t("brain.chat.typing")}
          />
        ) : null}
        {sending.error ? <InlineError message={errorMessage(sending.error)} /> : null}
        <ConversationComposer
          identity={id ?? "brain"}
          label={t("brain.chat.question")}
          placeholder={t("brain.chat.placeholder")}
          busy={thread.isPending || thread.isError || sending.pending || sessionId !== null}
          usage={thread.data?.usage}
          onSend={sending.send}
        />
      </div>
    </div>
  );
}
