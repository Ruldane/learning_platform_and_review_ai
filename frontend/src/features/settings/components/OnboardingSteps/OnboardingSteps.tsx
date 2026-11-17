import { useEffect, useRef, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { StepButtons } from "./StepButtons";

interface OnboardingStepsProps {
  /** L'étape affichée, à partir de 1. */
  step: number;
  total: number;
  title: string;
  /** Le libellé du bouton qui avance : « Suivant », « Plus tard », « Passer » ou « Terminer ». */
  nextLabel: string;
  /** La raison qui empêche d'avancer, dite et reliée au bouton ; absente : on peut avancer. */
  nextBlockedReason?: string;
  /** Un enregistrement est en cours : plus aucune action n'est prise. */
  busy: boolean;
  /** L'échec du dernier enregistrement, en français. */
  error: string | null;
  onPrevious: () => void;
  onNext: () => void;
  /** « Passer l'accueil » : terminer sans rien changer à la disponibilité. */
  onSkipAll: () => void;
  children: ReactNode;
}

/**
 * Le cadre d'une étape du premier lancement : « Étape 2 sur 5 », le titre, le contenu, puis les
 * boutons (`StepButtons`). Le titre prend le focus à chaque étape : le bouton cliqué change de
 * rôle ou disparaît, et sans cela la personne au clavier repartirait du haut de la page.
 */
export function OnboardingSteps({
  step,
  total,
  title,
  error,
  children,
  ...buttons
}: OnboardingStepsProps) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), [step]);
  return (
    <section aria-label={t("onboarding.page.label")} className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">
          {t("onboarding.steps.counter", { step, total })}
        </p>
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold focus:outline-none">
          {title}
        </h1>
      </header>
      {children}
      {error ? <InlineError message={error} /> : null}
      <StepButtons first={step === 1} {...buttons} />
    </section>
  );
}
