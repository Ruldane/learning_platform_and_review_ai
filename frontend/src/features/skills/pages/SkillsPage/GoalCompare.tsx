import { useNavigate } from "react-router";
import { ApiError } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { CompareTable } from "../../components/CompareTable";
import { useSkillCompare } from "../../hooks/useSkillCompare";
import { toCompareView } from "../../toView";
import { QueryPanel } from "./QueryPanel";

/**
 * The comparison with the goal's target role. Without a goal that has a program (404
 * `no_compare_target`), an empty state offers to create one.
 */
export function GoalCompare() {
  const query = useSkillCompare(true);
  const navigate = useNavigate();
  if (query.error instanceof ApiError && query.error.code === "no_compare_target") {
    return (
      <EmptyState
        title={t("skills.compareNone.title")}
        description={t("skills.compareNone.description")}
        action={{
          label: t("skills.compareNone.action"),
          onClick: () => void navigate("/learn/goals"),
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
              onClick: () => void navigate("/learn/goals"),
            }}
          />
        );
      }}
    </QueryPanel>
  );
}
