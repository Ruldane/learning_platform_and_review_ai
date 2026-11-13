import { t } from "@/shared/i18n/t";
import type { ExperienceView } from "../viewTypes";
import { ExperienceFields } from "./ExperienceFields";
import { blank } from "./profileDraft";
import { RowList } from "./RowList";
import { Section } from "./Section";

interface ExperiencesSectionProps {
  items: ExperienceView[];
  onChange: (items: ExperienceView[]) => void;
}

/** Les expériences : une ligne par poste, avec ses réalisations. */
export function ExperiencesSection({ items, onChange }: ExperiencesSectionProps) {
  return (
    <Section title={t("cv.profile.section.experiences")} count={items.length} path="experiences">
      <RowList
        items={items}
        onChange={onChange}
        blank={blank.experience}
        rowName={(n) => t("cv.profile.experience.row", { n })}
        addLabel={t("cv.profile.experience.add")}
        removeLabel={(n) => t("cv.profile.experience.remove", { n })}
      >
        {(item, index, patch) => <ExperienceFields item={item} index={index} patch={patch} />}
      </RowList>
    </Section>
  );
}
