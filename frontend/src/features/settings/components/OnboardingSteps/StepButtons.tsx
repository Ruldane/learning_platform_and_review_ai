import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface StepButtonsProps {
  /** Pas de « Précédent » sur la première étape. */
  first: boolean;
  nextLabel: string;
  nextBlockedReason?: string;
  busy: boolean;
  onPrevious: () => void;
  onNext: () => void;
  onSkipAll: () => void;
}

/**
 * Précédent, avancer, « Passer l'accueil ». Bloqués par `aria-disabled`, jamais `disabled` : le
 * focus reste sur le bouton cliqué et l'action est ignorée ; la raison d'un blocage est un texte
 * relié au bouton.
 */
export function StepButtons({
  first,
  nextLabel,
  nextBlockedReason,
  busy,
  onPrevious,
  onNext,
  onSkipAll,
}: StepButtonsProps) {
  const reasonId = useId();
  const blocked = busy || nextBlockedReason !== undefined;
  const unlessBusy = (action: () => void) => () => {
    if (!busy) action();
  };
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        {first ? null : (
          <Button variant="outline" aria-disabled={busy} onClick={unlessBusy(onPrevious)}>
            {t("onboarding.steps.previous")}
          </Button>
        )}
        <Button
          aria-disabled={blocked}
          aria-describedby={nextBlockedReason ? reasonId : undefined}
          onClick={() => {
            if (!blocked) onNext();
          }}
        >
          {busy ? t("onboarding.steps.finishing") : nextLabel}
        </Button>
        <Button variant="link" aria-disabled={busy} onClick={unlessBusy(onSkipAll)}>
          {t("onboarding.steps.skipAll")}
        </Button>
      </div>
      {nextBlockedReason ? (
        <p id={reasonId} className="text-sm text-muted-foreground">
          {nextBlockedReason}
        </p>
      ) : null}
    </>
  );
}
