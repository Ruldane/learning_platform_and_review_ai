import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { OnboardingSteps } from "../../components/OnboardingSteps";
import { useApiKeys } from "../../hooks/useApiKeys";
import { useCvDocuments } from "../../hooks/useCvDocuments";
import { useFinishOnboarding } from "../../hooks/useFinishOnboarding";
import { useImportProfile } from "../../hooks/useImportProfile";
import { useOnboardingAvailability } from "../../hooks/useOnboardingAvailability";
import { STEP_COUNT } from "../../onboarding";
import type { SettingsOut } from "../../types";
import { StepBody } from "./StepBody";

const TITLES = [
  "onboarding.steps.titles.health",
  "onboarding.steps.titles.privacy",
  "onboarding.steps.titles.key",
  "onboarding.steps.titles.cv",
  "onboarding.steps.titles.availability",
] as const;

/** Le bouton qui avance : « Plus tard » sans clé, « Passer » sans import, « Terminer » au bout. */
function nextLabel(step: number, hasKey: boolean, imported: boolean): string {
  if (step === STEP_COUNT) return t("onboarding.steps.finish");
  if (step === 3 && !hasKey) return t("onboarding.steps.later");
  if (step === 4 && !imported) return t("onboarding.steps.skipStep");
  return t("onboarding.steps.next");
}

/**
 * Les cinq étapes du premier lancement ; l'étape, les durées saisies et les PDF choisis vivent
 * ici, donc survivent au changement d'étape. Une clé existe dès qu'un fournisseur en a une (la
 * liste est lue dès l'ouverture de la page, l'étape 3 la partage).
 */
export function WelcomeSteps({ settings }: { settings: SettingsOut }) {
  const [step, setStep] = useState(1);
  const hasKey = useApiKeys().data?.some((entry) => entry.source !== null) ?? false;
  const documents = useCvDocuments();
  const importer = useImportProfile();
  const finisher = useFinishOnboarding();
  const availability = useOnboardingAvailability(settings, finisher.failure);
  const last = step === STEP_COUNT;
  // Un échec d'enregistrement ne suit pas à l'étape suivante : il parlait de celle d'avant.
  const goTo = (target: number | ((current: number) => number)) => {
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
      onPrevious={() => goTo((current) => current - 1)}
      onNext={() =>
        last ? void finisher.finish(settings, availability.values) : goTo((current) => current + 1)
      }
      onSkipAll={() => void finisher.finish(settings)}
    >
      <StepBody
        step={step}
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
