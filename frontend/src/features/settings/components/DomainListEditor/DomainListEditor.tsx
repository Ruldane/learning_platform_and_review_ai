import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { DomainChips } from "./DomainChips";
import { DomainInput } from "./DomainInput";
import { normalizeDomain } from "./normalizeDomain";

interface DomainListEditorProps {
  /** Intitulé du groupe (« Domaines privilégiés », « Domaines exclus »). */
  label: string;
  value: string[];
  onChange: (domains: string[]) => void;
  max?: number;
}

/**
 * Liste de domaines : ajout par champ et bouton (Entrée aussi), retrait par bouton. La saisie est
 * normalisée comme au back ; un domaine invalide, en double ou en trop donne un message en ligne.
 */
export function DomainListEditor({ label, value, onChange, max = 50 }: DomainListEditorProps) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const groupId = useId();

  function add() {
    if (draft.trim() === "") return;
    const domain = normalizeDomain(draft);
    if (domain === null) return setError(t("settings.search.domains.invalid"));
    if (value.includes(domain)) return setError(t("settings.search.domains.duplicate"));
    if (value.length >= max) return setError(t("settings.search.domains.full", { max }));
    onChange([...value, domain]);
    setDraft("");
    setError(null);
  }

  return (
    <div role="group" aria-labelledby={groupId} className="flex flex-col gap-2">
      <span id={groupId} className="text-sm font-medium">
        {label}
      </span>
      <DomainChips
        domains={value}
        onRemove={(domain) => onChange(value.filter((d) => d !== domain))}
      />
      <DomainInput
        draft={draft}
        error={error}
        onDraftChange={(next) => {
          setDraft(next);
          setError(null);
        }}
        onAdd={add}
      />
    </div>
  );
}
