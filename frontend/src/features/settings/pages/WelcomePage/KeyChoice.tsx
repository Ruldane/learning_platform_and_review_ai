import { useId, useState, type Ref } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { ApiKeyCard } from "../../components/ApiKeyCard";
import type { ApiKeyEntry } from "../../components/viewTypes";
import type { useKeyActions } from "../../hooks/useKeyActions";

interface KeyChoiceProps {
  entries: ApiKeyEntry[];
  actions: ReturnType<typeof useKeyActions>;
  /** Le choix du fournisseur : il reçoit le focus quand une lecture ratée réussit. */
  selectRef: Ref<HTMLSelectElement>;
}

/** Le fournisseur (celui qui a une clé d'abord) et sa carte : saisie, « Tester », suppression. */
export function KeyChoice({ entries, actions, selectRef }: KeyChoiceProps) {
  const [chosen, setChosen] = useState<string | null>(null);
  const selectId = useId();
  const entry =
    entries.find((item) => item.provider === chosen) ??
    entries.find((item) => item.source !== null) ??
    entries[0];
  if (!entry) return null;
  return (
    <>
      <div className="flex max-w-xs flex-col gap-1">
        <label htmlFor={selectId} className="text-sm font-medium">
          {t("onboarding.key.provider")}
        </label>
        <select
          id={selectId}
          ref={selectRef}
          value={entry.provider}
          onChange={(event) => setChosen(event.target.value)}
          className={fieldClass}
        >
          {entries.map((item) => (
            <option key={item.provider} value={item.provider}>
              {item.label}
            </option>
          ))}
        </select>
      </div>
      <ApiKeyCard
        entry={entry}
        testResult={actions.testResults[entry.provider]}
        pending={actions.pendingProviders.includes(entry.provider)}
        onSave={(key) => actions.onSave(entry.provider, key)}
        onDelete={() => actions.onDelete(entry.provider)}
        onTest={() => actions.onTest(entry.provider)}
      />
    </>
  );
}
