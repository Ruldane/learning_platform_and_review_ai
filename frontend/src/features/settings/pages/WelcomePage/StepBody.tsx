import { t } from "@/shared/i18n/t";
import { AvailabilityFields } from "../../components/AvailabilityFields";
import { CvImportStep } from "../../components/CvImportStep";
import { PrivacyNotice } from "../../components/PrivacyNotice";
import type { AvailabilityFlags, AvailabilityKey } from "../../components/viewTypes";
import type { ProfileImport } from "../../api";
import type { OnboardingAvailability } from "../../onboarding";
import { HealthStep } from "./HealthStep";
import { KeyStep } from "./KeyStep";

export interface StepBodyProps {
  step: number;
  onKeyConfigured: (configured: boolean) => void;
  importer: {
    pending: boolean;
    error: string | null;
    imported: boolean;
    start: (documents: ProfileImport) => void;
  };
  availability: {
    values: OnboardingAvailability;
    flags: AvailabilityFlags;
    refused: Partial<Record<AvailabilityKey, boolean>>;
    budget: number | null;
    onChange: (key: AvailabilityKey, value: string) => void;
  };
}

/** Le contenu de l'étape `step` ; chaque étape est un composant, la page ne fait que choisir. */
export function StepBody({ step, onKeyConfigured, importer, availability }: StepBodyProps) {
  switch (step) {
    case 1:
      return <HealthStep />;
    case 2:
      return <PrivacyNotice />;
    case 3:
      return <KeyStep onConfiguredChange={onKeyConfigured} />;
    case 4:
      return (
        <CvImportStep
          pending={importer.pending}
          error={importer.error}
          imported={importer.imported}
          onImport={importer.start}
        />
      );
    default:
      return (
        <div className="flex flex-col gap-4">
          <p className="text-muted-foreground">{t("onboarding.availability.intro")}</p>
          <AvailabilityFields {...availability} />
        </div>
      );
  }
}
