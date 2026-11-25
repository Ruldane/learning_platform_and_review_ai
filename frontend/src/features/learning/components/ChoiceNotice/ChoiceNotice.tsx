import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ChoiceNoticeProps {
  /** The Council's question (« Choisis un parcours… »). */
  question: string;
  answered: boolean;
  onShowProposals: () => void;
}

/**
 * The path choice question (breakpoint no. 2) in the thread: January answers it with the
 * cards in the Propositions tab, not with a field here; the card points there.
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
