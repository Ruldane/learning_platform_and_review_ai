import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

export function PostingUnavailable({
  error,
  retry,
  onList,
}: {
  error: unknown;
  retry: () => void;
  onList: () => void;
}) {
  if (error instanceof ApiError && error.status === 404) {
    return (
      <EmptyState
        title={t("gap.posting.notFoundTitle")}
        description={t("gap.errors.notFound")}
        action={{ label: t("gap.posting.notFoundAction"), onClick: onList }}
      />
    );
  }
  if (error) return <ErrorState message={errorMessage(error)} onRetry={retry} />;
  return <LoadingState label={t("gap.posting.loading")} />;
}
