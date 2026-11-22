import { useId } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useConversation } from "../../hooks/useConversation";
import { ConversationComposer } from "./ConversationComposer";
import { ConversationHeader } from "./ConversationHeader";
import { ConversationTranscript } from "./ConversationTranscript";

interface LessonConversationProps {
  lessonId: string;
  passage: LessonPassage | null;
  onClose: () => void;
}

export function LessonConversation({ lessonId, passage, onClose }: LessonConversationProps) {
  const id = useId();
  const { thread, sending, sessionId, streaming } = useConversation(lessonId);
  return (
    <section
      role="dialog"
      aria-labelledby={id}
      className="fixed inset-y-0 right-0 z-40 flex w-full max-w-xl flex-col border-l border-border bg-background shadow-xl"
    >
      <ConversationHeader
        id={id}
        lessonId={lessonId}
        excerpt={passage?.text ?? null}
        onClose={onClose}
      />
      {thread.isPending ? <LoadingState label={t("conversations.loading")} /> : null}
      {thread.isError ? (
        <InlineError message={errorMessage(thread.error)} onRetry={() => void thread.refetch()} />
      ) : null}
      {!thread.isPending && !thread.isError ? (
        <ConversationTranscript
          turns={thread.data?.turns ?? []}
          sessionId={sessionId}
          streaming={streaming}
        />
      ) : null}
      {sending.error ? <InlineError message={errorMessage(sending.error)} /> : null}
      <ConversationComposer
        identity={lessonId}
        label={t("conversations.question")}
        placeholder={t("conversations.placeholder")}
        busy={thread.isPending || thread.isError || sending.pending || sessionId !== null}
        passage={passage}
        usage={thread.data?.usage}
        onSend={sending.send}
      />
    </section>
  );
}
