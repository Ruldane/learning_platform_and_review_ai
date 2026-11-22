import { t } from "@/shared/i18n/t";
import { ChatMessage } from "@/shared/ui/ChatMessage";
import { ChatThread } from "@/shared/ui/ChatThread";
import type { ConversationTurn } from "../../api";
import { ConversationSources } from "./ConversationSources";

function messages(turn: ConversationTurn, live: string | null, assistant: string) {
  const question = (
    <ChatMessage
      key={`${turn.id}-question`}
      author="user"
      label={t("conversations.you")}
      content={turn.question}
      context={turn.passage}
    />
  );
  const failed =
    turn.status === "failed" || turn.status === "cancelled" || turn.status === "expired";
  const answer = turn.answer ?? (failed ? t("conversations.failed") : live);
  return answer
    ? [
        question,
        <ChatMessage
          key={`${turn.id}-answer`}
          author="assistant"
          allowLinks={false}
          label={assistant}
          content={answer}
        >
          <ConversationSources sources={turn.sources} />
        </ChatMessage>,
      ]
    : [question];
}

interface ConversationTranscriptProps {
  turns: ConversationTurn[];
  sessionId: string | null;
  streaming: string | null;
  assistant?: string;
  label?: string;
  greeting?: string;
  typing?: string;
  emptyText?: string;
}

export function ConversationTranscript({
  turns,
  sessionId,
  streaming,
  assistant = t("conversations.title"),
  label = t("conversations.thread"),
  greeting,
  typing = t("conversations.typing"),
  emptyText = t("conversations.empty"),
}: ConversationTranscriptProps) {
  return (
    <ChatThread
      label={label}
      emptyText={emptyText}
      scrollSignal={streaming ?? ""}
      footer={
        sessionId && !streaming ? (
          <p role="status" className="text-sm text-muted-foreground">
            {typing}
          </p>
        ) : null
      }
    >
      {[
        ...(greeting
          ? [<ChatMessage key="greeting" author="assistant" label={assistant} content={greeting} />]
          : []),
        ...turns.flatMap((turn) =>
          messages(turn, sessionId === turn.session_id ? streaming : null, assistant),
        ),
      ]}
    </ChatThread>
  );
}
