import { t } from "@/shared/i18n/t";
import type { LinkView } from "../viewTypes";
import { Field } from "./Field";
import { blank } from "./profileDraft";
import { RowList } from "./RowList";
import { Section } from "./Section";

interface LinksSectionProps {
  items: LinkView[];
  onChange: (items: LinkView[]) => void;
}

/** The links: a label and an address per row. */
export function LinksSection({ items, onChange }: LinksSectionProps) {
  return (
    <Section title={t("cv.profile.section.links")} count={items.length} path="links">
      <RowList
        items={items}
        onChange={onChange}
        blank={blank.link}
        rowName={(n) => t("cv.profile.link.row", { n })}
        addLabel={t("cv.profile.link.add")}
        removeLabel={(n) => t("cv.profile.link.remove", { n })}
      >
        {(item, index, patch) => (
          <>
            <Field
              path={`links.${index}.label`}
              label={t("cv.profile.link.label")}
              context={t("cv.profile.link.row", { n: index + 1 })}
              value={item.label}
              required
              onChange={(label) => patch({ label })}
            />
            <Field
              path={`links.${index}.url`}
              label={t("cv.profile.link.url")}
              context={t("cv.profile.link.row", { n: index + 1 })}
              value={item.url}
              required
              onChange={(url) => patch({ url })}
            />
          </>
        )}
      </RowList>
    </Section>
  );
}
