import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
  /** Libellé du bouton quand réessayer n'a pas de sens (ex. « Nouveau débat »). */
  actionLabel?: string;
}

/** Erreur affichée en place du contenu, avec un bouton pour réessayer (ou une autre issue). */
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
