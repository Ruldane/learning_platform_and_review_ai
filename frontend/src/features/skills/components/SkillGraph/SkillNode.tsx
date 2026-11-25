import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { t } from "@/shared/i18n/t";
import { LEVEL_COLORS, levelKey } from "../levels";
import type { LevelView } from "../viewTypes";

export type SkillFlowNode = Node<{ name: string; level: LevelView }, "skill">;

const HANDLE_CLASS = "!size-1 !min-h-0 !min-w-0 !border-0 !bg-transparent";

/**
 * A skill on the graph: background in the level's colour, name and level written out. Size comes
 * from the node (market demand). The attachment points only serve to draw the links.
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
