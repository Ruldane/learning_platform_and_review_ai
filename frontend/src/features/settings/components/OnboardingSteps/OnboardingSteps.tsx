import { useEffect, useId, useRef, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { StepButtons } from "./StepButtons";

interface OnboardingStepsProps {
  /** The step shown, starting at 1. */
  step: number;
  total: number;
  title: string;
  /** Advance label: « Suivant », « Plus tard », « Passer » or « Terminer ». */
  nextLabel: string;
  /** The reason that blocks moving on, stated and tied to the button; absent: can move on. */
  nextBlockedReason?: string;
  /** A save is in progress: no further action is taken. */
  busy: boolean;
  /** The error from the last save, in French. */
  error: string | null;
  onPrevious: () => void;
  onNext: () => void;
  /** « Passer l'accueil »: finish without changing availability. */
  onSkipAll: () => void;
  children: ReactNode;
}

/**
 * The frame of a first-run step: « Étape 2 sur 5 », the title, the content, then the
 * buttons (`StepButtons`). The title takes focus at each step: the clicked button changes
 * role or disappears, and without this the keyboard user would restart from the top. The
 * counter is tied to the title (`aria-describedby`): the screen reader reads it with it.
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
  const counterId = useId();
  useEffect(() => heading.current?.focus(), [step]);
  return (
    <section aria-label={t("onboarding.page.label")} className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <p id={counterId} className="text-sm text-muted-foreground">
          {t("onboarding.steps.counter", { step, total })}
        </p>
        <h1
          ref={heading}
          tabIndex={-1}
          aria-describedby={counterId}
          className="text-2xl font-semibold focus:outline-none"
        >
          {title}
        </h1>
      </header>
      {children}
      {error ? <InlineError message={error} /> : null}
      <StepButtons first={step === 1} {...buttons} />
    </section>
  );
}
