import { ProgressChart } from "../../components/ProgressChart";
import { useSkillHistory } from "../../hooks/useSkillHistory";
import { toHistoryView } from "../../toView";
import { QueryPanel } from "./QueryPanel";

/** L'onglet Progression : un relevé par semaine sur douze semaines. */
export function ProgressPanel() {
  const query = useSkillHistory(true);
  return (
    <QueryPanel query={query}>
      {(history) => <ProgressChart points={toHistoryView(history)} />}
    </QueryPanel>
  );
}
