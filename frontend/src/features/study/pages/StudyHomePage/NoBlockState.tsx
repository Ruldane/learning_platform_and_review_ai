import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";

/** No block today: the way out is to choose a lesson to study. */
export function NoBlockState() {
  const navigate = useNavigate();
  return (
    <EmptyState
      title={t("study.home.noBlockTitle")}
      description={t("study.home.noBlockDescription")}
      action={{
        label: t("study.home.chooseLesson"),
        onClick: () => void navigate("/learn/lessons"),
      }}
    />
  );
}
