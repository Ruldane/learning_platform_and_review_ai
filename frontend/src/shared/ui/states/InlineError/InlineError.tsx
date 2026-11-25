import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface InlineErrorProps {
  message: string;
  /** With `onRetry`, a « Réessayer » button follows the message (failed background re-read). */
  onRetry?: () => void;
}

/** An action's error, shown in the page without replacing it (announced by `role="alert"`). */
export function InlineError({ message, onRetry }: InlineErrorProps) {
  const text = (
    <p
      role="alert"
      className="rounded-lg border border-destructive/40 bg-card px-3 py-2 text-sm text-destructive"
    >
      {message}
    </p>
  );
  if (!onRetry) return text;
  return (
    <div className="flex flex-wrap items-center gap-3">
      {text}
      <Button variant="outline" onClick={onRetry}>
        {t("errors.retry")}
      </Button>
    </div>
  );
}
