import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { ProgressChart } from "../../components/ProgressChart";
import { useSkillHistory } from "../../hooks/useSkillHistory";
import { toHistoryView } from "../../toView";
import { QueryPanel } from "./QueryPanel";

/** L'onglet Progression : un relevé par semaine sur douze semaines. */
export function ProgressPanel() {
  const query = useSkillHistory(true);
  const navigate = useNavigate();
  const toStudy = {
    label: t("skills.progress.emptyAction"),
    onClick: () => void navigate("/etudier/session"),
  };
  return (
    <QueryPanel query={query}>
      {(history) => <ProgressChart points={toHistoryView(history)} emptyAction={toStudy} />}
    </QueryPanel>
  );
}
