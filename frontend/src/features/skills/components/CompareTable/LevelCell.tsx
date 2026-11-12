import { t } from "@/shared/i18n/t";
import { LEVEL_COLORS, levelKey } from "../levels";
import type { LevelView } from "../viewTypes";

/** Un niveau écrit en toutes lettres, avec sa couleur en repère. */
export function LevelCell({ level }: { level: LevelView }) {
  const key = levelKey(level);
  return (
    <td className="px-3 py-2">
      <span className="inline-flex items-center gap-1.5">
        <span
          aria-hidden="true"
          className="size-2.5 rounded-sm"
          style={{ backgroundColor: LEVEL_COLORS[key] }}
        />
        {t(`skills.level.${key}`)}
      </span>
    </td>
  );
}
