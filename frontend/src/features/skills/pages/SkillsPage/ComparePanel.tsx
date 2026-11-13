import { useNavigate } from "react-router";
import { ApiError } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { CompareTable } from "../../components/CompareTable";
import { useSkillCompare } from "../../hooks/useSkillCompare";
import { toCompareView } from "../../toView";
import { QueryPanel } from "./QueryPanel";

/**
 * L'onglet Comparaison avec le poste cible. Sans objectif qui ait un programme (404
 * `no_compare_target`), un état vide propose d'en créer un.
 */
export function ComparePanel() {
  const query = useSkillCompare(true);
  const navigate = useNavigate();
  if (query.error instanceof ApiError && query.error.code === "no_compare_target") {
    return (
      <EmptyState
        title={t("skills.compareNone.title")}
        description={t("skills.compareNone.description")}
        action={{
          label: t("skills.compareNone.action"),
          onClick: () => void navigate("/apprendre/objectifs"),
        }}
      />
    );
  }
  return (
    <QueryPanel query={query}>
      {(compare) => {
        const view = toCompareView(compare);
        return (
          <CompareTable
            rows={view.rows}
            coverage={view.coverage}
            targetLabel={view.targetLabel}
            emptyAction={{
              label: t("skills.compare.emptyAction"),
              onClick: () => void navigate("/apprendre/objectifs"),
            }}
          />
        );
      }}
    </QueryPanel>
  );
}
