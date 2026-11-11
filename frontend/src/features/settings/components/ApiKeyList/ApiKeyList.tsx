import { ApiKeyCard } from "../ApiKeyCard";
import type { ApiKeyEntry, KeyTestView } from "../viewTypes";

interface ApiKeyListProps {
  entries: ApiKeyEntry[];
  /** Résultats de test, par nom de fournisseur. */
  testResults: Record<string, KeyTestView>;
  /** Fournisseurs dont une opération est en cours. */
  pendingProviders: readonly string[];
  onSave: (provider: string, key: string) => void | Promise<void>;
  onDelete: (provider: string) => void;
  onTest: (provider: string) => void;
}

/** Une carte de clé par fournisseur. */
export function ApiKeyList({
  entries,
  testResults,
  pendingProviders,
  onSave,
  onDelete,
  onTest,
}: ApiKeyListProps) {
  return (
    <ul className="grid gap-3 md:grid-cols-2">
      {entries.map((entry) => (
        <li key={entry.provider}>
          <ApiKeyCard
            entry={entry}
            testResult={testResults[entry.provider]}
            pending={pendingProviders.includes(entry.provider)}
            onSave={(key) => onSave(entry.provider, key)}
            onDelete={() => onDelete(entry.provider)}
            onTest={() => onTest(entry.provider)}
          />
        </li>
      ))}
    </ul>
  );
}
