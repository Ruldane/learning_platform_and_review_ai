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
  /** Au moins un filtre est actif. */
  filtered: boolean;
  /** Le programme le plus récent, vers lequel renvoie l'état vide. */
  latestProgramId: string | null;
  onClearFilters: () => void;
  onToggleStatus: (resourceId: string, status: ResourceStatus) => void;
}

/** Le résultat de la bibliothèque : chargement, erreur, rien (avec une issue) ou la liste. */
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
