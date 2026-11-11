import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { BenchField } from "./BenchField";

interface BenchFieldsProps {
  query: string;
  urls: string;
  errors: { query?: string; urls?: string };
  disabled: boolean;
  onQueryChange: (query: string) => void;
  onUrlsChange: (urls: string) => void;
}

/** Les deux champs du formulaire d'essai : la requête et les adresses supplémentaires. */
export function BenchFields({
  query,
  urls,
  errors,
  disabled,
  onQueryChange,
  onUrlsChange,
}: BenchFieldsProps) {
  return (
    <>
      <BenchField
        label={t("research.bench.query")}
        hint={t("research.bench.queryHint")}
        error={errors.query}
      >
        {(props) => (
          <input
            {...props}
            type="text"
            value={query}
            disabled={disabled}
            onChange={(event) => onQueryChange(event.target.value)}
            className={fieldClass}
          />
        )}
      </BenchField>
      <BenchField
        label={t("research.bench.urls")}
        hint={t("research.bench.urlsHint")}
        error={errors.urls}
      >
        {(props) => (
          <textarea
            {...props}
            rows={3}
            value={urls}
            disabled={disabled}
            spellCheck={false}
            onChange={(event) => onUrlsChange(event.target.value)}
            className={`${fieldClass} h-auto py-1.5`}
          />
        )}
      </BenchField>
    </>
  );
}
