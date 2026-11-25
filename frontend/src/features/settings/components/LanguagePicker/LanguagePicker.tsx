import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { SEARCH_LANGUAGES } from "../viewTypes";
import type { SearchLanguage } from "../viewTypes";

interface LanguagePickerProps {
  /** Checked language codes (at least one). */
  value: string[];
  onChange: (languages: string[]) => void;
}

/**
 * The six search languages, as checkboxes. The last checked language is disabled: a
 * search with no language makes no sense. The rendered order is the list's order; an unknown code
 * already saved is kept at the end of the list rather than silently lost.
 */
export function LanguagePicker({ value, onChange }: LanguagePickerProps) {
  const legendId = useId();
  const hintId = useId();
  const extras = value.filter((code) => !SEARCH_LANGUAGES.includes(code as SearchLanguage));
  const toggle = (code: SearchLanguage) => {
    const next = value.includes(code) ? value.filter((c) => c !== code) : [...value, code];
    const known = SEARCH_LANGUAGES.filter((language) => next.includes(language));
    onChange([...known, ...extras]);
  };
  return (
    <div
      role="group"
      aria-labelledby={legendId}
      aria-describedby={hintId}
      className="flex flex-col gap-2"
    >
      <span id={legendId} className="text-sm font-medium">
        {t("settings.search.languages.label")}
      </span>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {SEARCH_LANGUAGES.map((code) => {
          const checked = value.includes(code);
          return (
            <label key={code} className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={checked}
                disabled={checked && value.length <= 1}
                onChange={() => toggle(code)}
              />
              {t(`settings.search.languages.${code}`)}
            </label>
          );
        })}
      </div>
      <p id={hintId} className="text-xs text-muted-foreground">
        {t("settings.search.languages.hint")}
      </p>
    </div>
  );
}
