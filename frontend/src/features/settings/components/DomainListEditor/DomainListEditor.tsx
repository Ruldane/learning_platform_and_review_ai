import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { DomainChips } from "./DomainChips";
import { DomainInput } from "./DomainInput";
import { normalizeDomain } from "./normalizeDomain";

interface DomainListEditorProps {
  /** Group title (« Domaines privilégiés », « Domaines exclus »). */
  label: string;
  value: string[];
  onChange: (domains: string[]) => void;
  max?: number;
}

/**
 * Domain list: add through a field and button (Enter too), remove through a button. Input is
 * normalized as on the back end; an invalid, duplicate or excessive domain gives an inline message.
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
