import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { SEARCH_LANGUAGES } from "../viewTypes";
import type { SearchLanguage } from "../viewTypes";

interface LanguagePickerProps {
  /** Codes de langue cochés (au moins un). */
  value: string[];
  onChange: (languages: string[]) => void;
}

/**
 * Les six langues de recherche, en cases à cocher. La dernière langue cochée est désactivée : une
 * recherche sans langue n'a pas de sens. L'ordre rendu est celui de la liste ; un code inconnu
 * déjà enregistré est conservé en fin de liste plutôt que perdu en silence.
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
