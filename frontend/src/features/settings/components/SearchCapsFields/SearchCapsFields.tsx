import { t } from "@/shared/i18n/t";
import { CapField } from "./CapField";

interface SearchCapsFieldsProps {
  maxQueries: number;
  maxPages: number;
  onChange: (caps: { maxQueries: number; maxPages: number }) => void;
}

/** Plafonds par session : requêtes (1 à 50) et pages lues (1 à 100). */
export function SearchCapsFields({ maxQueries, maxPages, onChange }: SearchCapsFieldsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <CapField
        label={t("settings.search.caps.maxQueries")}
        value={maxQueries}
        min={1}
        max={50}
        onValid={(value) => onChange({ maxQueries: value, maxPages })}
      />
      <CapField
        label={t("settings.search.caps.maxPages")}
        value={maxPages}
        min={1}
        max={100}
        onValid={(value) => onChange({ maxQueries, maxPages: value })}
      />
    </div>
  );
}
