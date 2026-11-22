import { useId, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import { ChatComposer } from "@/shared/ui/ChatComposer";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useConversation } from "../../hooks/useConversation";
import { ConversationHeader } from "./ConversationHeader";
import { ConversationSettings, type ConversationSource } from "./ConversationSettings";
import { ConversationTranscript } from "./ConversationTranscript";

interface LessonConversationProps {
  lessonId: string;
  passage: LessonPassage | null;
  onClose: () => void;
}

function useConversationSource(lessonId: string) {
  const key = `tremplin.conversation.source.${lessonId}`;
  const [source, setSource] = useState<ConversationSource>(() => {
    try {
      const saved = localStorage.getItem(key);
      return saved === "codex" || saved === "claude-code" ? saved : "settings";
    } catch {
      return "settings";
    }
  });
  return [
    source,
    (choice: ConversationSource) => {
      setSource(choice);
      try {
        localStorage.setItem(key, choice);
      } catch {
        // Le choix reste valable tant que le panneau est ouvert.
      }
    },
  ] as const;
}

export function LessonConversation({ lessonId, passage, onClose }: LessonConversationProps) {
  const id = useId();
  const { thread, sending, sessionId, streaming } = useConversation(lessonId);
  const [strong, setStrong] = useState(false);
  const [source, setSource] = useConversationSource(lessonId);
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
      <ChatComposer
        label={t("conversations.question")}
        placeholder={t("conversations.placeholder")}
        busy={thread.isPending || thread.isError || sending.pending || sessionId !== null}
        actions={
          <ConversationSettings
            source={source}
            onSourceChange={setSource}
            strong={strong}
            onStrongChange={setStrong}
            usage={thread.data?.usage}
          />
        }
        onSend={(question) =>
          sending.send(question, passage, source === "settings" && strong, source)
        }
      />
    </section>
  );
}
