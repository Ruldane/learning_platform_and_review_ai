import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
  /** Button label when retrying makes no sense (e.g. « Nouveau débat »). */
  actionLabel?: string;
}

/** Error shown in place of the content, with a button to retry (or another outcome). */
export function ErrorState({ message, onRetry, actionLabel }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-xl border border-destructive/40 bg-card px-6 py-10 text-center"
    >
      <p className="text-destructive">{message}</p>
      <Button variant="outline" onClick={onRetry}>
        {actionLabel ?? t("errors.retry")}
      </Button>
    </div>
  );
}
