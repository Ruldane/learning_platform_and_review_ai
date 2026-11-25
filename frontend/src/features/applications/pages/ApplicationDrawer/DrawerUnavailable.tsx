import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface DrawerUnavailableProps {
  /** The read error, or `null` while it loads. */
  error: unknown;
  onRetry: () => void;
  onBack: () => void;
}

/** What the drawer shows until the record is there: loading, unknown record (404) or failure. */
export function DrawerUnavailable({ error, onRetry, onBack }: DrawerUnavailableProps) {
  if (error instanceof ApiError && error.status === 404) {
    return (
      <EmptyState
        title={t("applications.drawer.notFoundTitle")}
        description={t("applications.errors.application_not_found")}
        action={{ label: t("applications.drawer.notFoundAction"), onClick: onBack }}
      />
    );
  }
  if (error) return <ErrorState message={errorMessage(error)} onRetry={onRetry} />;
  return <LoadingState label={t("applications.drawer.loading")} />;
}
