import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { InterruptCard } from "@/shared/session-ui";
import type { Run } from "@/shared/realtime/useRun";
import { canAnswer, type InterruptItem } from "@/shared/session-ui";

export const TEMPLATE_QUESTION = "cv_template";
export const MAX_INSTRUCTION = 500;

/** Une consigne d'ajustement ne dépasse jamais 500 caractères. */
function capped(value: unknown): unknown {
  if (typeof value !== "object" || value === null || !("answers" in value)) return value;
  const { answers } = value;
  const text =
    typeof answers === "object" && answers !== null && "instruction" in answers
      ? answers.instruction
      : "";
  const instruction = (typeof text === "string" ? text : "").slice(0, MAX_INSTRUCTION);
  return { answers: { instruction } };
}

/**
 * La question du Maquettiste : « Valider », « Ajuster » avec une consigne, « Recommencer la capture ».
 * Une consigne saisie ne change pas « Valider » ni « Recommencer » en ajustement ; « Ajuster » sans
 * consigne n'envoie rien et dit quoi faire (le back reposerait la même question).
 */
export function TemplateQuestion({ item, run }: { item: InterruptItem; run: Run }) {
  const [missing, setMissing] = useState(false);
  const { interrupt, answered } = item;
  const answer = (value: unknown) => {
    if (value === "adjust") {
      setMissing(true);
      return;
    }
    setMissing(false);
    void run.actions.resume(interrupt.interrupt_id, capped(value));
  };
  return (
    <div className="flex flex-col gap-2">
      <InterruptCard
        interrupt={interrupt}
        answered={answered}
        disabled={!canAnswer(run, item)}
        onAnswer={answer}
        optionWithAnswers={(value, answers) => (value === "adjust" ? { answers } : value)}
      />
      {missing && !answered ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("cv.templatePage.adjustFirst")}
        </p>
      ) : null}
    </div>
  );
}
