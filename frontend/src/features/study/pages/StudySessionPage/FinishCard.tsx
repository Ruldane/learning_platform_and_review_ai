import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface FinishCardProps {
  question: string;
  answered: boolean;
  canFinish: boolean;
  onFinish: () => void;
}

/** The Tutor's closing question: « Terminer la session » (via `PATCH finish`, time saved). */
export function FinishCard({ question, answered, canFinish, onFinish }: FinishCardProps) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="rounded-xl border-2 border-primary bg-card px-4 py-3"
    >
      <p id={titleId} className="font-medium">
        {question}
      </p>
      {answered ? null : (
        <>
          <p className="mt-1 text-sm text-muted-foreground">{t("study.session.finishCardHint")}</p>
          <Button className="mt-2" disabled={!canFinish} onClick={onFinish}>
            {t("study.session.finishCard")}
          </Button>
        </>
      )}
    </section>
  );
}
