import { useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { concentrationDrop, type ResponseTiming } from "@/shared/lib/concentration";
import { getRunSource } from "@/shared/lib/runSource";
import { useResponseClock } from "@/shared/lib/useResponseClock";
import type { ConversationTurn } from "../../api";
import { useSend } from "../../hooks/useConversation";
import { readConversationSource } from "../../hooks/useConversationSource";
import { sendTrainingQuestion, type TrainingSession } from "../../trainingApi";

function needsAdaptation(turns: ConversationTurn[], timings: ResponseTiming[]) {
  const outcomes = new Map(
    turns.map((turn) => [turn.session_id, turn.status === "completed" ? turn.focus_outcome : null]),
  );
  return concentrationDrop(
    timings.flatMap(({ id, milliseconds }) => {
      const outcome = outcomes.get(id);
      return outcome ? [{ milliseconds, missed: outcome === "retry" }] : [];
    }),
  );
}

function remember(history: ResponseTiming[], timing: ResponseTiming, limit: number) {
  return history.length < limit && !history.some((item) => item.id === timing.id)
    ? [...history, timing]
    : history;
}

interface Options {
  session: TrainingSession;
  busy: boolean;
  onSubmitted: (id: string) => void;
  restoreFocus: () => void;
}

export function useTrainingConcentration({ session, busy, onSubmitted, restoreFocus }: Options) {
  const [choice, setChoice] = useState<"waiting" | "paused" | "closed">("waiting");
  const [timings, setTimings] = useState<ResponseTiming[]>([]);
  const accepted = useRef<string | null>(null);
  const send = useSend(
    (message, source) => sendTrainingQuestion(session.id, message, source),
    (id) => {
      accepted.current = id;
      onSubmitted(id);
    },
  );
  const { turns, usage } = session.conversation;
  const paused = choice === "paused";
  const clock = useResponseClock(
    !paused && !busy && !send.pending && turns.at(-1)?.status === "completed",
  );
  const submit: typeof send.send = async (...args) => {
    const elapsed = clock.take();
    accepted.current = null;
    const result = await send.send(...args);
    const id = accepted.current;
    if (result && id && elapsed !== null) {
      setTimings((history) => remember(history, { id, milliseconds: elapsed }, usage.turn_limit));
    }
    return result;
  };
  const close = () => {
    setChoice("closed");
    requestAnimationFrame(restoreFocus);
  };
  const easier = async () => {
    const source = readConversationSource(session.id) ?? getRunSource();
    if (await send.send(t("concentration.trainingRequest"), null, false, source)) close();
  };
  const phase = paused
    ? "paused"
    : choice === "waiting" && needsAdaptation(turns, timings)
      ? "suggested"
      : null;
  return {
    phase,
    paused,
    send,
    activity: () => clock.activity(),
    submit,
    easier,
    close,
    pause: () => setChoice("paused"),
  } as const;
}
