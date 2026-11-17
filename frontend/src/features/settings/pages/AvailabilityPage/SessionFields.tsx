import { t } from "@/shared/i18n/t";
import {
  ROUNDS_RANGE,
  TOKEN_CAP_MIN,
  type AvailabilityDraft,
  type AvailabilityErrors,
  type AvailabilityField,
} from "../../availabilitySettings";
import { NumberField } from "../../components/NumberField";
import { Section } from "../../components/Section";
import { BriefFields } from "./BriefFields";
import { LanguageField } from "./LanguageField";

interface SessionFieldsProps {
  draft: AvailabilityDraft;
  errors: AvailabilityErrors;
  refused: (field: AvailabilityField) => boolean;
  onChange: (next: AvailabilityDraft) => void;
}

/** Heure du brief, délais de relance, tours de débat, plafond par session, langue des leçons. */
export function SessionFields({ draft, errors, refused, onChange }: SessionFieldsProps) {
  return (
    <>
      <Section title={t("settings.availability.sections.brief")}>
        <BriefFields
          draft={draft}
          timeInvalid={errors.briefTime}
          timeRefused={refused("briefTime")}
          delaysInvalid={errors.delays}
          delaysRefused={refused("delays")}
          onChange={onChange}
        />
      </Section>
      <Section title={t("settings.availability.sections.sessions")}>
        <div className="flex flex-wrap gap-6">
          <NumberField
            label={t("settings.availability.rounds")}
            value={draft.rounds}
            {...ROUNDS_RANGE}
            invalid={errors.rounds}
            refused={refused("rounds")}
            onChange={(rounds) => onChange({ ...draft, rounds })}
          />
          <NumberField
            label={t("settings.availability.tokenCap")}
            value={draft.tokenCap}
            hint={t("settings.fields.atLeast", { min: TOKEN_CAP_MIN.toLocaleString("fr-FR") })}
            invalid={errors.tokenCap}
            refused={refused("tokenCap")}
            onChange={(tokenCap) => onChange({ ...draft, tokenCap })}
          />
        </div>
      </Section>
      <Section title={t("settings.availability.sections.language")}>
        <LanguageField
          value={draft.lessonLanguage}
          onChange={(lessonLanguage) => onChange({ ...draft, lessonLanguage })}
        />
      </Section>
    </>
  );
}
