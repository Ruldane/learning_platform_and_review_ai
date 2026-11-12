import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ChoiceNoticeProps {
  /** La question du Conseil (« Choisis un parcours… »). */
  question: string;
  answered: boolean;
  onShowProposals: () => void;
}

/**
 * La question du choix du parcours (point d'arrêt n° 2) dans le fil : January y répond par les
 * cartes de l'onglet Propositions, pas par un champ ici ; la carte y renvoie.
 */
export function ChoiceNotice({ question, answered, onShowProposals }: ChoiceNoticeProps) {
  const questionId = useId();
  return (
    <section
      aria-labelledby={questionId}
      className="rounded-xl border-2 border-primary bg-card px-4 py-3"
    >
      <p id={questionId} className="font-medium">
        {question}
      </p>
      {answered ? (
        <p className="mt-2 text-sm text-muted-foreground">{t("session.interrupt.answered")}</p>
      ) : (
        <>
          <p className="mt-1 text-sm text-muted-foreground">{t("learning.council.choosePath")}</p>
          <Button variant="outline" className="mt-2" onClick={onShowProposals}>
            {t("learning.council.showProposals")}
          </Button>
        </>
      )}
    </section>
  );
}
