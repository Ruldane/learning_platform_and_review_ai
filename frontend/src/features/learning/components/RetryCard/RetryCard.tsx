import { useId, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface RetryCardProps {
  /** What failed, in one sentence (absent: the failure is already said above). */
  title?: string;
  /** What the retry does. */
  help: string;
  actionLabel: string;
  busy: boolean;
  launchMenu?: ReactNode;
  /** A re-read refusal (conflict): information, not an error. */
  notice: string | null;
  error: string | null;
  onRetry: () => void;
}

/** A failed step and the button that retries it, with the refusal or error of the retry. */
export function RetryCard(props: RetryCardProps) {
  const { title, help, actionLabel, busy, notice, error, onRetry, launchMenu } = props;
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
      {launchMenu}
      <Button className="self-start" disabled={busy} aria-describedby={helpId} onClick={onRetry}>
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
