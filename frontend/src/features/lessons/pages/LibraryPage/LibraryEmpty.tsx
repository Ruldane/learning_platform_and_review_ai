import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";

interface LibraryEmptyProps {
  /** At least one filter is active: no resource matches. */
  filtered: boolean;
  latestProgramId: string | null;
  onClearFilters: () => void;
}

/** Empty library: filters to clear, or a link to the program the resources will come from. */
export function LibraryEmpty({ filtered, latestProgramId, onClearFilters }: LibraryEmptyProps) {
  const navigate = useNavigate();
  if (filtered) {
    return (
      <EmptyState
        title={t("lessons.library.noMatchTitle")}
        description={t("lessons.library.noMatchDescription")}
        action={{ label: t("lessons.library.noMatchAction"), onClick: onClearFilters }}
      />
    );
  }
  const programPath = latestProgramId
    ? `/learn/programs/${latestProgramId}`
    : "/learn/programs";
  return (
    <EmptyState
      title={t("lessons.library.emptyTitle")}
      description={t("lessons.library.emptyDescription")}
      action={{
        label: t("lessons.library.emptyAction"),
        onClick: () => void navigate(programPath),
      }}
    />
  );
}
