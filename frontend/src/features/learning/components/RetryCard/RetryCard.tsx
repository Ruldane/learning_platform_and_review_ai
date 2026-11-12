import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface RetryCardProps {
  /** Ce qui a échoué, en une phrase (absent : l'échec est déjà dit au-dessus). */
  title?: string;
  /** Ce que fait la relance. */
  help: string;
  actionLabel: string;
  busy: boolean;
  /** Refus relu (conflit) : une information, pas une erreur. */
  notice: string | null;
  error: string | null;
  onRetry: () => void;
}

/** Une étape en échec et le bouton qui la relance, avec le refus ou l'erreur de la relance. */
export function RetryCard(props: RetryCardProps) {
  const { title, help, actionLabel, busy, notice, error, onRetry } = props;
  const helpId = useId();
  return (
    <section
      aria-label={actionLabel}
      className="flex flex-col gap-2 rounded-xl border border-destructive/40 bg-card px-4 py-3"
    >
      {title ? <p className="font-medium">{title}</p> : null}
      <p id={helpId} className="text-sm text-muted-foreground">
        {help}
      </p>
      <Button
        className="self-start"
        disabled={busy}
        aria-describedby={helpId}
        onClick={onRetry}
      >
        {busy ? t("learning.retry.busy") : actionLabel}
      </Button>
      {notice ? (
        <p role="status" className="text-sm">
          {notice}
        </p>
      ) : null}
      {error ? <InlineError message={error} /> : null}
    </section>
  );
}
