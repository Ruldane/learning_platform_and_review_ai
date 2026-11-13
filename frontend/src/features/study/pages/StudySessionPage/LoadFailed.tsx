import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";

/** La session n'a pas pu être lue : introuvable (état vide), ou une erreur à réessayer. */
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
