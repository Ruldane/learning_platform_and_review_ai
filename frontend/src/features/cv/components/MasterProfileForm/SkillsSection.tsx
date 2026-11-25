import { t } from "@/shared/i18n/t";
import type { SkillFactView } from "../viewTypes";
import { Field } from "./Field";
import { blank } from "./profileDraft";
import { RowList } from "./RowList";
import { Section } from "./Section";

interface SkillsSectionProps {
  items: SkillFactView[];
  onChange: (items: SkillFactView[]) => void;
}

/** Skills: a name and an optional category per row. */
export function SkillsSection({ items, onChange }: SkillsSectionProps) {
  return (
    <Section title={t("cv.profile.section.skills")} count={items.length} path="skills">
      <RowList
        items={items}
        onChange={onChange}
        blank={blank.skill}
        rowName={(n) => t("cv.profile.skill.row", { n })}
        addLabel={t("cv.profile.skill.add")}
        removeLabel={(n) => t("cv.profile.skill.remove", { n })}
      >
        {(item, index, patch) => (
          <>
            <Field
              path={`skills.${index}.name`}
              label={t("cv.profile.skill.name")}
              context={t("cv.profile.skill.row", { n: index + 1 })}
              value={item.name}
              required
              onChange={(name) => patch({ name })}
            />
            <Field
              path={`skills.${index}.category`}
              label={t("cv.profile.skill.category")}
              context={t("cv.profile.skill.row", { n: index + 1 })}
              value={item.category ?? ""}
              onChange={(category) => patch({ category: category || null })}
            />
          </>
        )}
      </RowList>
    </Section>
  );
}
