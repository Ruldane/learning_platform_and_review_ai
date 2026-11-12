import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { RetryCard } from "../../components/RetryCard";
import type { useRetryCouncil } from "../../hooks/useRetryCouncil";

interface CouncilFailureProps {
  /** Message de `run.failed`, s'il est arrivé par le direct. */
  message: string | null;
  retry: ReturnType<typeof useRetryCouncil>;
}

/** Le Conseil a échoué : la raison, puis « Relancer le Conseil » (il repart du début). */
export function CouncilFailure({ message, retry }: CouncilFailureProps) {
  return (
    <>
      {message ? <InlineError message={message} /> : null}
      <RetryCard
        title={message ? undefined : t("learning.council.councilFailed")}
        help={t("learning.retry.councilHelp")}
        actionLabel={t("learning.retry.council")}
        busy={retry.pending}
        notice={retry.notice}
        error={retry.error}
        onRetry={() => void retry.retry()}
      />
    </>
  );
}
