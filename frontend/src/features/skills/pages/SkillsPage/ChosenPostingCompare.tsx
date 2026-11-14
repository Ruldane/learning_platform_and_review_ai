import { useNavigate } from "react-router";
import { ApiError } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { CompareTable } from "../../components/CompareTable";
import { useSkillCompare } from "../../hooks/useSkillCompare";
import { toCompareView } from "../../toView";
import { QueryPanel } from "./QueryPanel";

/** La comparaison avec l'offre choisie ; une offre dont l'écart n'est pas rangé se dit en clair. */
export function ChosenPostingCompare({ postingId }: { postingId: string }) {
  const query = useSkillCompare(true, postingId);
  const navigate = useNavigate();
  if (query.error instanceof ApiError && query.error.code === "no_compare_target") {
    return <p role="status">{t("skills.compare.postingNotReady")}</p>;
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
              label: t("skills.compare.noPostingsAction"),
              onClick: () => void navigate("/carriere/offres"),
            }}
          />
        );
      }}
    </QueryPanel>
  );
}
