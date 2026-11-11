import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";

/** État vide d'un écran de la mémoire : explique et propose « Importer un document ». */
export function ImportEmptyState({ title }: { title: string }) {
  const navigate = useNavigate();
  return (
    <EmptyState
      title={title}
      description={t("memory.page.emptyDescription")}
      action={{
        label: t("memory.page.importDocument"),
        onClick: () => void navigate("/memoire/documents"),
      }}
    />
  );
}
