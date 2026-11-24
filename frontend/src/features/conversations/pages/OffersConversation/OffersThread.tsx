import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ChatComposer } from "@/shared/ui/ChatComposer";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useThread } from "../../hooks/useConversation";
import { threadKey } from "../../hooks/useConversationList";
import { readOffersThread, sendOffersQuestion } from "../../offersApi";
import { ConversationTranscript } from "../LessonConversation/ConversationTranscript";
import { SuggestedQuestions } from "./SuggestedQuestions";

export function OffersThread({ id, onSubmitted }: { id: string; onSubmitted: () => void }) {
  const { thread, sessionId, streaming, sending } = useThread({
    key: threadKey("offers", id),
    read: (signal) => readOffersThread(id, signal),
    submit: (message) => sendOffersQuestion(id, message),
    agent: "offers_adviser",
    onSubmitted,
  });
  if (thread.isPending) return <LoadingState label={t("conversations.loading")} />;
  if (thread.isError) {
    return (
      <InlineError message={errorMessage(thread.error)} onRetry={() => void thread.refetch()} />
    );
  }
  const turns = thread.data?.turns ?? [];
  const busy = sending.pending || sessionId !== null;
  const send = (question: string) => sending.send(question, null, false, "settings");
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border">
      <ConversationTranscript
        turns={turns}
        sessionId={sessionId}
        streaming={streaming}
        assistant={t("conversations.offers.assistant")}
        label={t("conversations.offers.thread")}
        emptyText={t("conversations.offers.context")}
        typing={t("conversations.offers.typing")}
      />
      {turns.length === 0 && !busy ? (
        <SuggestedQuestions onSelect={(question) => void send(question)} />
      ) : null}
      {sending.error ? <InlineError message={errorMessage(sending.error)} /> : null}
      <ChatComposer
        label={t("conversations.offers.question")}
        placeholder={t("conversations.offers.placeholder")}
        busy={busy}
        onSend={send}
      />
    </div>
  );
}
