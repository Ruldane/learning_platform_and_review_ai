import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { ApiKeyForm } from "../ApiKeyForm";
import { ApiKeySummary } from "../ApiKeySummary";
import type { ApiKeyEntry, KeyTestView } from "../viewTypes";

interface ApiKeyCardProps {
  entry: ApiKeyEntry;
  /** Result of the last test run from this screen. */
  testResult?: KeyTestView;
  /** An operation on this provider is in progress: all buttons are disabled. */
  pending: boolean;
  /** May return a promise: if it fails, the input is kept so the user can retry. */
  onSave: (key: string) => void | Promise<void>;
  onDelete: () => void;
  onTest: () => void;
}

/** API key of a provider: status, masked input, test (result announced) and deletion. */
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
        {/* Only a key typed here is deleted; a key from .env is removed from the file. */}
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
