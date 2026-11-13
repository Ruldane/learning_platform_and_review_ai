import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { SkillEdgeView, SkillNodeView } from "../viewTypes";
import { PlacedGraph } from "./PlacedGraph";

export interface SkillGraphProps {
  nodes: SkillNodeView[];
  edges: SkillEdgeView[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** L'action de l'état vide (règle 15.4 : jamais d'impasse). */
  emptyAction?: { label: string; onClick: () => void };
}

/**
 * Carte des compétences : un nœud par compétence (couleur = niveau, taille = demande du marché), un
 * lien par prérequis, de gauche à droite. Lecture seule : les nœuds ne se déplacent pas, mais se
 * parcourent avec Tab et s'ouvrent avec Entrée ou Espace. La vue se déplace et se zoome avec les
 * commandes ; la molette garde son rôle de défilement de la page.
 */
export function SkillGraph(props: SkillGraphProps) {
  if (props.nodes.length === 0) {
    return (
      <EmptyState
        title={t("skills.graph.empty")}
        description={t("skills.graph.emptyHint")}
        action={props.emptyAction}
      />
    );
  }
  return <PlacedGraph {...props} />;
}
