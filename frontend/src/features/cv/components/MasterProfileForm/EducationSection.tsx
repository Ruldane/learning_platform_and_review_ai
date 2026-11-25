import { t } from "@/shared/i18n/t";
import type { EducationView } from "../viewTypes";
import { EducationFields } from "./EducationFields";
import { blank } from "./profileDraft";
import { RowList } from "./RowList";
import { Section } from "./Section";

interface EducationSectionProps {
  items: EducationView[];
  onChange: (items: EducationView[]) => void;
}

/** The education section: one row per degree. */
export function EducationSection({ items, onChange }: EducationSectionProps) {
  return (
    <Section title={t("cv.profile.section.education")} count={items.length} path="education">
      <RowList
        items={items}
        onChange={onChange}
        blank={blank.education}
        rowName={(n) => t("cv.profile.education.row", { n })}
        addLabel={t("cv.profile.education.add")}
        removeLabel={(n) => t("cv.profile.education.remove", { n })}
      >
        {(item, index, patch) => <EducationFields item={item} index={index} patch={patch} />}
      </RowList>
    </Section>
  );
}
