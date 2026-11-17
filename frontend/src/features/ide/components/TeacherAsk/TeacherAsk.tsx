import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { QuestionForm } from "./QuestionForm";

interface TeacherAskProps {
  /** Le professeur travaille déjà, ou une demande part : les boutons ignorent les clics. */
  busy: boolean;
  /** Une exécution a échoué : « Pourquoi cette erreur ? » a quelque chose à expliquer. */
  canExplain: boolean;
  onHint: () => void;
  onWhy: () => void;
  onQuestion: (question: string) => void;
}

/**
 * Les trois façons d'appeler le professeur : un indice, l'explication d'une erreur, une question.
 * Occupé, un bouton reste focalisable (`aria-disabled`) : le focus ne tombe pas sur `body`.
 */
export function TeacherAsk({ busy, canExplain, onHint, onWhy, onQuestion }: TeacherAskProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          aria-disabled={busy}
          onClick={busy ? undefined : onHint}
        >
          {t("ide.teacher.hint")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!canExplain}
          aria-disabled={busy}
          onClick={busy ? undefined : onWhy}
        >
          {t("ide.teacher.why")}
        </Button>
      </div>
      <QuestionForm busy={busy} onQuestion={onQuestion} />
    </div>
  );
}
