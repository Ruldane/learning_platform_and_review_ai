import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { ApiKeyForm } from "../ApiKeyForm";
import { ApiKeySummary } from "../ApiKeySummary";
import type { ApiKeyEntry, KeyTestView } from "../viewTypes";

interface ApiKeyCardProps {
  entry: ApiKeyEntry;
  /** Résultat du dernier test lancé depuis cet écran. */
  testResult?: KeyTestView;
  /** Une opération sur ce fournisseur est en cours : tous les boutons sont désactivés. */
  pending: boolean;
  /** Peut renvoyer une promesse : si elle échoue, la saisie est conservée pour réessayer. */
  onSave: (key: string) => void | Promise<void>;
  onDelete: () => void;
  onTest: () => void;
}

/** Clé API d'un fournisseur : état, saisie masquée, test (résultat annoncé) et suppression. */
export function ApiKeyCard({
  entry,
  testResult,
  pending,
  onSave,
  onDelete,
  onTest,
}: ApiKeyCardProps) {
  const headingId = useId();
  return (
    <article
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
    >
      <ApiKeySummary entry={entry} headingId={headingId} />
      <ApiKeyForm providerLabel={entry.label} pending={pending} onSave={onSave} />
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" disabled={pending || !entry.source} onClick={onTest}>
          {t("settings.keys.test")}
        </Button>
        {/* Seule une clé saisie ici se supprime ; celle du fichier .env se retire du fichier. */}
        {entry.source === "ui" ? (
          <Button variant="destructive" disabled={pending} onClick={onDelete}>
            {t("settings.keys.delete")}
          </Button>
        ) : null}
        <p
          role="status"
          className={cn("text-sm", testResult?.ok ? "text-emerald-700" : "text-destructive")}
        >
          {testResult?.message}
        </p>
      </div>
    </article>
  );
}
