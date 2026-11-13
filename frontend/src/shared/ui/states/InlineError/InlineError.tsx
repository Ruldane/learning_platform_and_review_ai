import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface InlineErrorProps {
  message: string;
  /** Avec `onRetry`, un bouton « Réessayer » suit le message (relecture ratée en arrière-plan). */
  onRetry?: () => void;
}

/** Erreur d'une action, affichée dans la page sans la remplacer (annoncée par `role="alert"`). */
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
