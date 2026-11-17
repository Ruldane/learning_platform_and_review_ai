import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { SEARCH_LANGUAGES, type SearchLanguage } from "../../components/viewTypes";

const isListed = (code: string): code is SearchLanguage =>
  (SEARCH_LANGUAGES as readonly string[]).includes(code);

/**
 * La langue des leçons ; la langue enregistrée reste proposée même si la liste ne la connaît pas.
 */
export function LanguageField({
  value,
  onChange,
}: {
  value: string;
  onChange: (code: string) => void;
}) {
  const codes: string[] = isListed(value) ? [...SEARCH_LANGUAGES] : [value, ...SEARCH_LANGUAGES];
  return (
    <label className="text-sm font-medium">
      {t("settings.availability.lessonLanguage")}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`${fieldClass} mt-1 block w-48`}
      >
        {codes.map((code) => (
          <option key={code} value={code}>
            {isListed(code) ? t(`settings.search.languages.${code}`) : code}
          </option>
        ))}
      </select>
    </label>
  );
}
