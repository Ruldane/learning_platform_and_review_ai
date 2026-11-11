import { t } from "@/shared/i18n/t";
import { ApiKeyList } from "../ApiKeyList";
import type { ApiKeyEntry, KeyTestView } from "../viewTypes";

interface KeysSectionProps {
  entries: ApiKeyEntry[];
  testResults: Record<string, KeyTestView>;
  pendingProviders: readonly string[];
  onSave: (provider: string, key: string) => void | Promise<void>;
  onDelete: (provider: string) => void;
  onTest: (provider: string) => void;
}

/** Section « Clés API » : titre, explication et une carte par fournisseur. */
export function KeysSection({ entries, ...actions }: KeysSectionProps) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-medium">{t("settings.keys.title")}</h2>
      <p className="text-muted-foreground">{t("settings.keys.intro")}</p>
      <ApiKeyList entries={entries} {...actions} />
    </section>
  );
}
