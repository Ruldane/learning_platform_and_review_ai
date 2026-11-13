import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";

/** Pas de bloc aujourd'hui : l'issue est de choisir une leçon à étudier. */
export function NoBlockState() {
  const navigate = useNavigate();
  return (
    <EmptyState
      title={t("study.home.noBlockTitle")}
      description={t("study.home.noBlockDescription")}
      action={{
        label: t("study.home.chooseLesson"),
        onClick: () => void navigate("/apprendre/lecons"),
      }}
    />
  );
}
