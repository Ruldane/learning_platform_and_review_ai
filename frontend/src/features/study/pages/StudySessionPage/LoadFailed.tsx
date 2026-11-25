import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";

/** The session could not be read: not found (empty state), or an error to retry. */
export function LoadFailed(props: { error: unknown; onRetry: () => void; onHome: () => void }) {
  if (props.error instanceof ApiError && props.error.status === 404) {
    return (
      <EmptyState
        title={t("study.session.notFoundTitle")}
        description={t("study.session.notFoundDescription")}
        action={{ label: t("study.session.back"), onClick: props.onHome }}
      />
    );
  }
  return <ErrorState message={errorMessage(props.error)} onRetry={props.onRetry} />;
}
