import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { t } from "@/shared/i18n/t";
import { LEVEL_COLORS, levelKey } from "../levels";
import type { LevelView } from "../viewTypes";

export type SkillFlowNode = Node<{ name: string; level: LevelView }, "skill">;

const HANDLE_CLASS = "!size-1 !min-h-0 !min-w-0 !border-0 !bg-transparent";

/**
 * Une compétence sur le graphe : fond de la couleur du niveau, nom et niveau écrits. La taille vient
 * du nœud (demande du marché). Les points d'attache ne servent qu'à tracer les liens.
 */
export function SkillNode({ data, selected }: NodeProps<SkillFlowNode>) {
  const key = levelKey(data.level);
  return (
    <div
      data-level={key}
      className={`flex size-full flex-col justify-center rounded-md px-2 text-white ${
        selected ? "outline-2 outline-offset-2 outline-foreground" : ""
      }`}
      style={{ backgroundColor: LEVEL_COLORS[key] }}
    >
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={false}
        className={HANDLE_CLASS}
      />
      <span className="line-clamp-2 text-sm leading-tight font-medium">{data.name}</span>
      <span className="text-xs">{t(`skills.level.${key}`)}</span>
      <Handle
        type="source"
        position={Position.Right}
        isConnectable={false}
        className={HANDLE_CLASS}
      />
    </div>
  );
}
