import type { Run } from "@/shared/realtime/useRun";
import { canAnswer, type InterruptItem } from "@/shared/session-ui";
import { InterviewQuestionCard } from "../../components/InterviewQuestionCard";
import { ANSWER_KIND, questionPosition } from "./questionPosition";

const STOP = "stop";

/**
 * La carte d'une question de l'entretien (`interview_answer`) ; `undefined` pour tout autre
 * question (la carte commune du fil s'en charge). Répondre envoie `{ answers: { answer } }`,
 * « Terminer l'entretien » envoie la valeur de l'option (`stop`).
 */
export function renderQuestion(item: InterruptItem, run: Run, total: number) {
  if (item.interrupt.kind !== ANSWER_KIND) return undefined;
  const position = questionPosition(run.stream.view.feed, item);
  const id = item.interrupt.interrupt_id;
  const stop = item.interrupt.options?.find((option) => option.value === STOP);
  return (
    <InterviewQuestionCard
      number={position?.number ?? null}
      total={total}
      followUp={position?.followUp ?? false}
      answered={item.answered}
      disabled={!canAnswer(run, item)}
      stopLabel={stop?.label ?? null}
      onAnswer={(text) => void run.actions.resume(id, { answers: { answer: text } })}
      onStop={() => void run.actions.resume(id, STOP)}
    />
  );
}
