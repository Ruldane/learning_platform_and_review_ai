import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { AvailabilityFields } from "../../components/AvailabilityFields";
import { CvImportStep } from "../../components/CvImportStep";
import { PrivacyNotice } from "../../components/PrivacyNotice";
import type { CvDocuments } from "../../components/viewTypes";
import type { AvailabilityFlags, AvailabilityKey } from "../../components/viewTypes";
import type { ProfileImport } from "../../api";
import type { OnboardingAvailability } from "../../onboarding";
import type { SettingsOut } from "../../types";
import { HealthStep } from "./HealthStep";
import { KeyStep } from "./KeyStep";

export interface StepBodyProps {
  step: number;
  settings: SettingsOut;
  /** Une clé d'API existe (`.env` ou saisie) : l'import du CV en a besoin. */
  hasKey: boolean;
  documents: CvDocuments;
  onGoToKey: () => void;
  importer: {
    launchMenu: ReactNode;
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
export function StepBody(props: StepBodyProps) {
  const { step, settings, hasKey, documents, onGoToKey, importer, availability } = props;
  switch (step) {
    case 1:
      return <HealthStep />;
    case 2:
      return <PrivacyNotice />;
    case 3:
      return <KeyStep settings={settings} />;
    case 4:
      return (
        <CvImportStep
          documents={documents}
          hasKey={hasKey}
          onGoToKey={onGoToKey}
          pending={importer.pending}
          error={importer.error}
          imported={importer.imported}
          launchMenu={importer.launchMenu}
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
