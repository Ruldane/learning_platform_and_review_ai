import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { RetryCard } from "../../components/RetryCard";
import type { useProgramRetry } from "../../hooks/useProgramRetry";

interface ProgramStateProps {
  /** Link to the program, as soon as it is ready. */
  link: string | null;
  /** The program session failed without a saved program. */
  failed: boolean;
  retry: ReturnType<typeof useProgramRetry>;
}

/** At the program stage: the link when ready, its restart if it failed, otherwise the wait. */
export function ProgramState({ link, failed, retry }: ProgramStateProps) {
  if (link) {
    return (
      <p className="text-sm">
        <Link to={link} className="font-medium underline underline-offset-2">
          {t("learning.council.programLink")}
        </Link>
      </p>
    );
  }
  if (failed && retry.retry) {
    return (
      <RetryCard
        title={t("learning.council.programFailed")}
        help={t("learning.retry.programHelp")}
        actionLabel={t("learning.retry.program")}
        busy={retry.pending}
        notice={retry.notice}
        error={retry.error}
        onRetry={retry.retry}
      />
    );
  }
  if (failed) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {t("learning.council.programFailed")}
      </p>
    );
  }
  return (
    <p className="text-sm">
      <span role="status" className="text-muted-foreground">
        {t("learning.council.programPending")}
      </span>
    </p>
  );
}
