import { useState } from "react";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import { useRunSource } from "@/shared/lib/runSource";
import { ChatComposer } from "@/shared/ui/ChatComposer";
import type { Conversation } from "../../api";
import type { useSend } from "../../hooks/useConversation";
import { useConversationSource } from "../../hooks/useConversationSource";
import { ConversationSettings } from "./ConversationSettings";

interface ConversationComposerProps {
  identity: string;
  label: string;
  placeholder: string;
  initialText?: string;
  busy: boolean;
  passage?: LessonPassage | null;
  usage?: Conversation["usage"];
  onSend: ReturnType<typeof useSend>["send"];
}

export function ConversationComposer({
  identity,
  label,
  placeholder,
  initialText,
  busy,
  passage,
  usage,
  onSend,
}: ConversationComposerProps) {
  const [strong, setStrong] = useState(false);
  const [source, setSource] = useConversationSource(identity);
  const [global] = useRunSource();
  const effective = source ?? global;
  const played = effective === "codex" || effective === "claude-code";
  return (
    <ChatComposer
      label={label}
      placeholder={placeholder}
      initialText={initialText}
      busy={busy}
      actions={
        <ConversationSettings
          source={source}
          onSourceChange={setSource}
          relay={played}
          strong={strong}
          onStrongChange={setStrong}
          usage={usage}
        />
      }
      onSend={(question) => onSend(question, passage ?? null, !played && strong, effective)}
    />
  );
}
