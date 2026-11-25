import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { RetryCard } from "../../components/RetryCard";
import type { useRetryCouncil } from "../../hooks/useRetryCouncil";

interface CouncilFailureProps {
  /** Message of `run.failed`, if it arrived through the live feed. */
  message: string | null;
  retry: ReturnType<typeof useRetryCouncil>;
}

/** The Council failed: the reason, then « Relancer le Conseil » (restarts from the beginning). */
export function CouncilFailure({ message, retry }: CouncilFailureProps) {
  return (
    <>
      {message ? <InlineError message={message} /> : null}
      <RetryCard
        title={message ? undefined : t("learning.council.councilFailed")}
        help={t("learning.retry.councilHelp")}
        actionLabel={t("learning.retry.council")}
        busy={retry.pending}
        launchMenu={retry.launchMenu}
        notice={retry.notice}
        error={retry.error}
        onRetry={() => void retry.retry()}
      />
    </>
  );
}
