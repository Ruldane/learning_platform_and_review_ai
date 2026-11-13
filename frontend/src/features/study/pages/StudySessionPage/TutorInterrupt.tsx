import { isAwaitingAnswer } from "@/shared/realtime/feedHelpers";
import type { FeedItem } from "@/shared/realtime/types";
import { InterruptCard } from "@/shared/session-ui";
import { TutorQuestionCard } from "../../components/TutorQuestionCard";
import type { StudyRun } from "../../hooks/useStudyRun";
import { toTutorOptions } from "../../toView";
import { FinishCard } from "./FinishCard";

type InterruptItem = Extract<FeedItem, { kind: "interrupt" }>;

const TUTOR_QUESTION = "tutor_question";
const FINISH_SESSION = "finish_session";

/** La valeur de l'option `value` donnée par le back ; sa valeur de repli est celle du contrat. */
const optionValue = (options: { value: string }[], value: string) =>
  options.find((option) => option.value === value)?.value ?? value;

interface TutorInterruptProps {
  item: InterruptItem;
  run: StudyRun;
}

/**
 * Une question du Tuteur dans le fil. Une question de section, d'exercice ou finale : la carte du
 * Tuteur (« Je bloque », « Passer » viennent du back, la réponse part par sa valeur). La question
 * de fin : « Terminer la session », qui passe par `PATCH finish` (le temps est enregistré), jamais
 * par la reprise générique. Les autres genres gardent la carte commune.
 */
export function TutorInterrupt({ item, run }: TutorInterruptProps) {
  const { interrupt, answered } = item;
  const { stream, actions } = run;
  const awaiting = isAwaitingAnswer(stream.view, interrupt.interrupt_id);
  const disabled = actions.pending || !awaiting;
  const answer = (value: unknown) => void actions.resume(interrupt.interrupt_id, value);

  if (interrupt.kind === TUTOR_QUESTION) {
    const options = toTutorOptions(interrupt.options);
    return (
      <TutorQuestionCard
        question={interrupt.question}
        options={options}
        answered={answered}
        disabled={disabled}
        onAnswer={(text) => answer({ answers: { answer: text } })}
        onStuck={() => answer(optionValue(options, "stuck"))}
        onSkip={() => answer(optionValue(options, "skip"))}
      />
    );
  }
  if (interrupt.kind === FINISH_SESSION) {
    return (
      <FinishCard
        question={interrupt.question}
        answered={answered}
        canFinish={run.canFinish}
        onFinish={() => void run.finish()}
      />
    );
  }
  return (
    <InterruptCard
      interrupt={interrupt}
      answered={answered}
      disabled={disabled}
      onAnswer={answer}
    />
  );
}
