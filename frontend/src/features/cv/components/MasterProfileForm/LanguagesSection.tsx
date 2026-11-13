import { t } from "@/shared/i18n/t";
import type { LanguageView } from "../viewTypes";
import { Field } from "./Field";
import { blank } from "./profileDraft";
import { RowList } from "./RowList";
import { Section } from "./Section";

interface LanguagesSectionProps {
  items: LanguageView[];
  onChange: (items: LanguageView[]) => void;
}

/** Les langues : un nom et un niveau facultatif par ligne. */
export function LanguagesSection({ items, onChange }: LanguagesSectionProps) {
  return (
    <Section title={t("cv.profile.section.languages")} count={items.length} path="languages">
      <RowList
        items={items}
        onChange={onChange}
        blank={blank.language}
        rowName={(n) => t("cv.profile.language.row", { n })}
        addLabel={t("cv.profile.language.add")}
        removeLabel={(n) => t("cv.profile.language.remove", { n })}
      >
        {(item, index, patch) => (
          <>
            <Field
              path={`languages.${index}.name`}
              label={t("cv.profile.language.name")}
              context={t("cv.profile.language.row", { n: index + 1 })}
              value={item.name}
              required
              onChange={(name) => patch({ name })}
            />
            <Field
              path={`languages.${index}.level`}
              label={t("cv.profile.language.level")}
              context={t("cv.profile.language.row", { n: index + 1 })}
              value={item.level ?? ""}
              onChange={(level) => patch({ level: level || null })}
            />
          </>
        )}
      </RowList>
    </Section>
  );
}
