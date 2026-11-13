import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { SkillRadar } from "../../components/SkillRadar";
import { useSkillGraph } from "../../hooks/useSkillGraph";
import { toGraphView } from "../../toView";
import { QueryPanel } from "./QueryPanel";

/** L'onglet Radar : le score de chaque domaine, lu avec le graphe. */
export function RadarPanel() {
  const query = useSkillGraph();
  const navigate = useNavigate();
  const toGoals = {
    label: t("skills.radar.emptyAction"),
    onClick: () => void navigate("/apprendre/objectifs"),
  };
  return (
    <QueryPanel query={query}>
      {(graph) => <SkillRadar domains={toGraphView(graph).domains} emptyAction={toGoals} />}
    </QueryPanel>
  );
}
