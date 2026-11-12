import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";

interface LibraryEmptyProps {
  /** Au moins un filtre est actif : aucune ressource ne correspond. */
  filtered: boolean;
  latestProgramId: string | null;
  onClearFilters: () => void;
}

/** Bibliothèque vide : filtres à effacer, ou lien vers le programme dont viendront les ressources. */
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
    ? `/apprendre/programme/${latestProgramId}`
    : "/apprendre/programme";
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
