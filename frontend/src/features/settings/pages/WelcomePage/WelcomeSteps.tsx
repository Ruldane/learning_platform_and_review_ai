import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { OnboardingSteps } from "../../components/OnboardingSteps";
import { useCvDocuments } from "../../hooks/useCvDocuments";
import { useFinishOnboarding } from "../../hooks/useFinishOnboarding";
import { useKeyPlan } from "../../hooks/useKeyPlan";
import { useImportProfile } from "../../hooks/useImportProfile";
import { useOnboardingAvailability } from "../../hooks/useOnboardingAvailability";
import { STEP_COUNT } from "../../onboarding";
import type { KeyPlan } from "../../keyPlan";
import type { SettingsOut } from "../../types";
import { StepBody } from "./StepBody";

const TITLES = [
  "onboarding.steps.titles.health",
  "onboarding.steps.titles.privacy",
  "onboarding.steps.titles.key",
  "onboarding.steps.titles.cv",
  "onboarding.steps.titles.availability",
] as const;

/** Advance: « Plus tard » (no key), « Passer » (no import), « Terminer » at the end. */
function nextLabel(step: number, hasKey: boolean, imported: boolean): string {
  if (step === STEP_COUNT) return t("onboarding.steps.finish");
  if (step === 3 && !hasKey) return t("onboarding.steps.later");
  if (step === 4 && !imported) return t("onboarding.steps.skipStep");
  return t("onboarding.steps.next");
}

interface AdvanceArgs {
  step: number;
  plan: KeyPlan | undefined;
  settings: SettingsOut;
  availability: ReturnType<typeof useOnboardingAvailability>;
  finisher: ReturnType<typeof useFinishOnboarding>;
  goTo: (target: number) => void;
}

/**
 * What the advance button does: finish on the last step; on step 3, first set
 * the models to the key's provider if needed (the step is left only once the send
 * succeeded); otherwise go to the next step.
 */
function advance({ step, plan, settings, availability, finisher, goTo }: AdvanceArgs): void {
  if (step === STEP_COUNT) return void finisher.finish(settings, availability.values);
  if (step === 3 && plan?.tiers) {
    finisher.reset();
    return void finisher.saveTiers(settings, plan.tiers).then((saved) => saved && goTo(4));
  }
  goTo(step + 1);
}

/**
 * The five first-run steps; the step, the typed durations and the chosen PDFs live
 * here, so they survive a step change. A key counts when it is the provider of the
 * models (`planKeys`); if it is another model provider's, its levels are set to
 * it when leaving step 3, before the CV import that reads with these models.
 */
export function WelcomeSteps({ settings }: { settings: SettingsOut }) {
  const [step, setStep] = useState(1);
  const { plan } = useKeyPlan(settings);
  const hasKey = plan?.ready ?? false;
  const documents = useCvDocuments();
  const importer = useImportProfile();
  const finisher = useFinishOnboarding();
  const availability = useOnboardingAvailability(settings, finisher.failure);
  const last = step === STEP_COUNT;
  // A save failure does not carry over to the next step: it was about the previous one.
  const goTo = (target: number) => {
    finisher.reset();
    setStep(target);
  };
  return (
    <OnboardingSteps
      step={step}
      total={STEP_COUNT}
      title={t(TITLES[step - 1] ?? TITLES[STEP_COUNT - 1]!)}
      nextLabel={nextLabel(step, hasKey, importer.imported)}
      nextBlockedReason={last && availability.invalid ? t("onboarding.steps.blocked") : undefined}
      busy={finisher.pending}
      error={finisher.error}
      onPrevious={() => goTo(step - 1)}
      onNext={() => advance({ step, plan, settings, availability, finisher, goTo })}
      onSkipAll={() => void finisher.finish(settings)}
    >
      <StepBody
        step={step}
        settings={settings}
        hasKey={hasKey}
        documents={documents}
        onGoToKey={() => goTo(3)}
        importer={importer}
        availability={{
          ...availability,
          onChange: (key, value) => {
            finisher.reset();
            availability.edit(key, value);
          },
        }}
      />
    </OnboardingSteps>
  );
}
