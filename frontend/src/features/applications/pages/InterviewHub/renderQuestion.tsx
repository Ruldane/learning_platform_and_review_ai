import type { Run } from "@/shared/realtime/useRun";
import { canAnswer, type InterruptItem } from "@/shared/session-ui";
import { InterviewQuestionCard } from "../../components/InterviewQuestionCard";
import { ANSWER_KIND, questionPosition } from "./questionPosition";

const STOP = "stop";

/**
 * The card for an interview question (`interview_answer`); `undefined` for any other
 * question (the thread's shared card handles it). Answering sends `{ answers: { answer } }`,
 * « Terminer l'entretien » sends the option's value (`stop`).
 */
export function renderQuestion(
  item: InterruptItem,
  run: Run,
  total: number,
  onStopped: () => void,
) {
  if (item.interrupt.kind !== ANSWER_KIND) return undefined;
  const position = questionPosition(run.stream.view.feed, item);
  const id = item.interrupt.interrupt_id;
  const stop = item.interrupt.options?.find((option) => option.value === STOP);
  return (
    <InterviewQuestionCard
      number={position?.number ?? null}
      total={total}
      question={item.interrupt.question}
      followUp={position?.followUp ?? false}
      answered={item.answered}
      disabled={!canAnswer(run, item)}
      stopLabel={stop?.label ?? null}
      onAnswer={(text) => void run.actions.resume(id, { answers: { answer: text } })}
      onStop={() => {
        onStopped();
        void run.actions.resume(id, STOP);
      }}
    />
  );
}
