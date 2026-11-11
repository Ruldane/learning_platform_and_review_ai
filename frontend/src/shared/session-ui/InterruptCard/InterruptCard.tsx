import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { InterruptPayload } from "@/shared/realtime/types";
import { Button } from "@/shared/ui/button";
import { FreeTextAnswer } from "../FreeTextAnswer";

interface InterruptCardProps {
  interrupt: InterruptPayload;
  answered: boolean;
  disabled?: boolean;
  onAnswer: (value: string) => void;
}

/**
 * Question de l'équipe, affichée comme une carte dans le fil (jamais `window.confirm`).
 * Les options sont des boutons ; sans option, un champ libre apparaît. Au clavier : le focus
 * arrive sur la première option (ou sur le champ), Tab passe d'une option à l'autre, Entrée valide.
 */
export function InterruptCard({
  interrupt,
  answered,
  disabled = false,
  onAnswer,
}: InterruptCardProps) {
  const questionId = useId();
  const locked = answered || disabled;
  const options = interrupt.options ?? [];

  return (
    <section
      aria-labelledby={questionId}
      className="rounded-xl border-2 border-primary bg-card px-4 py-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
    >
      <p id={questionId} className="font-medium">
        {interrupt.question}
      </p>
      {options.length > 0 ? (
        <div role="group" aria-labelledby={questionId} className="mt-2 flex flex-wrap gap-2">
          {options.map((option, index) => (
            <Button
              key={option.value}
              variant="outline"
              disabled={locked}
              autoFocus={!locked && index === 0}
              onClick={() => onAnswer(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      ) : (
        <FreeTextAnswer disabled={locked} onSubmit={onAnswer} />
      )}
      {answered ? (
        <p className="mt-2 text-sm text-muted-foreground">{t("session.interrupt.answered")}</p>
      ) : null}
    </section>
  );
}
