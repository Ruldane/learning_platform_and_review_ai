import { t } from "@/shared/i18n/t";
import { BraveUsageMeter } from "../../components/BraveUsageMeter";
import { DomainListEditor } from "../../components/DomainListEditor";
import { LanguagePicker } from "../../components/LanguagePicker";
import { ProviderOrderEditor } from "../../components/ProviderOrderEditor";
import { SearchCapsFields } from "../../components/SearchCapsFields";
import type { BraveUsageView, SearchSettingsView } from "../../types";
import { Section } from "./Section";

interface SearchSettingsSectionsProps {
  value: SearchSettingsView;
  usage: BraveUsageView;
  onChange: (next: SearchSettingsView) => void;
}

/** Les trois blocs de l'écran : requêtes (langues, plafonds), moteurs (ordre, Brave), domaines. */
export function SearchSettingsSections({ value, usage, onChange }: SearchSettingsSectionsProps) {
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
