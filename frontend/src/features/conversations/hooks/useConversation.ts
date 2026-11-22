import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import type { RunSource } from "@/shared/lib/runSource";
import { useRun } from "@/shared/realtime/useRun";
import {
  fetchConversation,
  sendQuestion,
  type Conversation,
  type ConversationMessage,
  type ConversationTurn,
} from "../api";

const active = (turn: ConversationTurn) =>
  turn.status === "running" || turn.status === "waiting_user" || turn.status === "paused";

export function following(
  turns: ConversationTurn[] | undefined,
  submitted: string | null,
): string | null {
  const last = turns?.at(-1);
  if (last && active(last)) return last.session_id;
  return turns?.some((turn) => turn.session_id === submitted) ? null : submitted;
}

type Submit = (message: ConversationMessage, source: RunSource) => Promise<{ session_id: string }>;

export function useSend(submit: Submit, started: (sessionId: string) => void) {
  const remembered = useRef<{ message: ConversationMessage; source: RunSource }>(null);
  const mutation = useMutation({
    mutationFn: ({ message, source }: NonNullable<typeof remembered.current>) =>
      submit(message, source),
  });
  const send = async (
    question: string,
    selected: LessonPassage | null,
    strong: boolean,
    source: RunSource,
  ) => {
    const passage = selected?.text ?? null;
    const passageOccurrence = selected?.occurrence ?? null;
    const prev = remembered.current;
    const unchanged =
      prev?.message.question === question &&
      prev.message.passage === passage &&
      prev.message.passage_occurrence === passageOccurrence &&
      prev.message.strong === strong &&
      prev.source === source;
    const attempt = unchanged
      ? prev
      : {
          message: {
            request_id: crypto.randomUUID(),
            question,
            passage,
            passage_occurrence: passageOccurrence,
            strong,
          },
          source,
        };
    remembered.current = attempt;
    try {
      const result = await mutation.mutateAsync(attempt);
      remembered.current = null;
      started(result.session_id);
      return true;
    } catch {
      return false;
    }
  };
  return { send, error: mutation.error, pending: mutation.isPending };
}

interface ThreadOptions {
  key: readonly string[];
  read: (signal?: AbortSignal) => Promise<Pick<Conversation, "id" | "turns" | "usage"> | null>;
  submit: Submit;
  agent: string;
}

export function useThread({ key, read, submit, agent }: ThreadOptions) {
  const [submitted, setSubmitted] = useState<string | null>(null);
  const thread = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => read(signal),
    refetchInterval: (query) => (following(query.state.data?.turns, submitted) ? 2_000 : false),
  });
  const sessionId = following(thread.data?.turns, submitted);
  const refresh = () => void thread.refetch();
  const streaming = useTurnStream(sessionId, agent, refresh);
  const sending = useSend(submit, (id) => {
    setSubmitted(id);
    refresh();
  });
  return { thread, sending, sessionId, streaming };
}

export function useConversation(lessonId: string) {
  return useThread({
    key: ["conversations", "lesson", lessonId],
    read: (signal) => fetchConversation(lessonId, signal),
    submit: (message, source) => sendQuestion(lessonId, message, source),
    agent: "lesson_professor",
  });
}

export function useTurnStream(sessionId: string | null, agent: string, onChange: () => void) {
  const run = useRun(sessionId, onChange);
  const partial = run.stream.view.feed.findLast(
    (item) => item.kind === "turn" && item.agent === agent,
  );
  return partial?.kind === "turn" ? partial.text : null;
}
