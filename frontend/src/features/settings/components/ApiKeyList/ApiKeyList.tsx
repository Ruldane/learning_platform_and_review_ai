import { ApiKeyCard } from "../ApiKeyCard";
import type { ApiKeyEntry, KeyTestView } from "../viewTypes";

interface ApiKeyListProps {
  entries: ApiKeyEntry[];
  /** Résultats de test, par nom de fournisseur. */
  testResults: Record<string, KeyTestView>;
  /** Fournisseur dont une opération est en cours, ou `null`. */
  pendingProvider: string | null;
  onSave: (provider: string, key: string) => void | Promise<void>;
  onDelete: (provider: string) => void;
  onTest: (provider: string) => void;
}

/** Une carte de clé par fournisseur. */
export function ApiKeyList({
  entries,
  testResults,
  pendingProvider,
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
            pending={pendingProvider === entry.provider}
            onSave={(key) => onSave(entry.provider, key)}
            onDelete={() => onDelete(entry.provider)}
            onTest={() => onTest(entry.provider)}
          />
        </li>
      ))}
    </ul>
  );
}
