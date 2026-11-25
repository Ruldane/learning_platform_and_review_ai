import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ResourceList } from "../../components/ResourceList";
import { useResources } from "../../hooks/useResources";
import type { LibraryFilterValue, ResourceStatus } from "../../types";
import { LibraryEmpty } from "./LibraryEmpty";

interface LibraryResultsProps {
  filters: LibraryFilterValue;
  /** At least one filter is active. */
  filtered: boolean;
  /** The newest program, which the empty state points to. */
  latestProgramId: string | null;
  onClearFilters: () => void;
  onToggleStatus: (resourceId: string, status: ResourceStatus) => void;
}

/** The library result: loading, error, nothing (with a reason) or the list. */
export function LibraryResults({
  filters,
  filtered,
  latestProgramId,
  onClearFilters,
  onToggleStatus,
}: LibraryResultsProps) {
  const resources = useResources(filters);
  if (resources.isPending) return <LoadingState label={t("lessons.library.loading")} />;
  if (resources.isError) {
    return (
      <ErrorState
        message={errorMessage(resources.error)}
        onRetry={() => void resources.refetch()}
      />
    );
  }
  if (resources.data.length === 0) {
    return (
      <LibraryEmpty
        filtered={filtered}
        latestProgramId={latestProgramId}
        onClearFilters={onClearFilters}
      />
    );
  }
  return (
    <section aria-label={t("lessons.resources.heading")} className="flex flex-col gap-2">
      <p className="text-sm text-muted-foreground" role="status">
        {t("lessons.library.count", { count: resources.data.length })}
      </p>
      <ResourceList resources={resources.data} onToggleStatus={onToggleStatus} />
    </section>
  );
}
