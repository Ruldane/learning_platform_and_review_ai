import { SkillRadar } from "../../components/SkillRadar";
import { useSkillGraph } from "../../hooks/useSkillGraph";
import { toGraphView } from "../../toView";
import { QueryPanel } from "./QueryPanel";

/** L'onglet Radar : le score de chaque domaine, lu avec le graphe. */
export function RadarPanel() {
  const query = useSkillGraph();
  return (
    <QueryPanel query={query}>
      {(graph) => <SkillRadar domains={toGraphView(graph).domains} />}
    </QueryPanel>
  );
}
