import { t } from "@/shared/i18n/t";
import { BraveUsageMeter } from "../../components/BraveUsageMeter";
import { DomainListEditor } from "../../components/DomainListEditor";
import { LanguagePicker } from "../../components/LanguagePicker";
import { ProviderOrderEditor } from "../../components/ProviderOrderEditor";
import { SearchCapsFields } from "../../components/SearchCapsFields";
import type { BraveUsageView, SearchSettingsView } from "../../types";
import { Section } from "../../components/Section";

interface SearchSettingsSectionsProps {
  value: SearchSettingsView;
  usage: BraveUsageView;
  onChange: (next: SearchSettingsView) => void;
  /** True while a cap holds an invalid entry. */
  onCapsInvalidChange: (invalid: boolean) => void;
}

/** The three blocks of the screen: queries (languages, caps), engines (order, Brave), domains. */
export function SearchSettingsSections({
  value,
  usage,
  onChange,
  onCapsInvalidChange,
}: SearchSettingsSectionsProps) {
  return (
    <>
      <Section title={t("settings.search.sections.queries")}>
        <LanguagePicker
          value={value.languages}
          onChange={(languages) => onChange({ ...value, languages })}
        />
        <SearchCapsFields
          maxQueries={value.maxQueries}
          maxPages={value.maxPages}
          onChange={(caps) => onChange({ ...value, ...caps })}
          onInvalidChange={onCapsInvalidChange}
        />
      </Section>
      <Section title={t("settings.search.sections.engines")}>
        <ProviderOrderEditor
          value={value.order}
          braveAvailable={usage.hasKey}
          onChange={(order) => onChange({ ...value, order })}
        />
        <BraveUsageMeter usage={usage} />
      </Section>
      <Section title={t("settings.search.sections.domains")}>
        <DomainListEditor
          label={t("settings.search.domainsPreferred")}
          value={value.preferred}
          onChange={(preferred) => onChange({ ...value, preferred })}
        />
        <DomainListEditor
          label={t("settings.search.domainsExcluded")}
          value={value.excluded}
          onChange={(excluded) => onChange({ ...value, excluded })}
        />
      </Section>
    </>
  );
}
