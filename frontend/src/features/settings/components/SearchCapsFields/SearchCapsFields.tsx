import { useCallback, useEffect, useState } from "react";
import { t } from "@/shared/i18n/t";
import { CapField } from "./CapField";

interface SearchCapsFieldsProps {
  maxQueries: number;
  maxPages: number;
  onChange: (caps: { maxQueries: number; maxPages: number }) => void;
  /** Vrai tant qu'un des deux champs contient une saisie invalide (l'envoi doit être refusé). */
  onInvalidChange?: (invalid: boolean) => void;
}

/** Plafonds par session : requêtes (1 à 50) et pages lues (1 à 100). */
export function SearchCapsFields({
  maxQueries,
  maxPages,
  onChange,
  onInvalidChange,
}: SearchCapsFieldsProps) {
  const [queriesInvalid, setQueriesInvalid] = useState(false);
  const [pagesInvalid, setPagesInvalid] = useState(false);
  const anyInvalid = queriesInvalid || pagesInvalid;
  useEffect(() => {
    onInvalidChange?.(anyInvalid);
    return () => onInvalidChange?.(false);
  }, [anyInvalid, onInvalidChange]);
  const onQueriesInvalid = useCallback((invalid: boolean) => setQueriesInvalid(invalid), []);
  const onPagesInvalid = useCallback((invalid: boolean) => setPagesInvalid(invalid), []);

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <CapField
        label={t("settings.search.caps.maxQueries")}
        value={maxQueries}
        min={1}
        max={50}
        onValid={(value) => onChange({ maxQueries: value, maxPages })}
        onInvalidChange={onQueriesInvalid}
      />
      <CapField
        label={t("settings.search.caps.maxPages")}
        value={maxPages}
        min={1}
        max={100}
        onValid={(value) => onChange({ maxQueries, maxPages: value })}
        onInvalidChange={onPagesInvalid}
      />
    </div>
  );
}
