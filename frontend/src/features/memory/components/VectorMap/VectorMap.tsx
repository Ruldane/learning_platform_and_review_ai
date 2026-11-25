import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { MEMORY_KINDS } from "../kindColors";
import { KindBadge } from "../KindBadge";
import type { MapPointView } from "../viewTypes";
import { MapCanvas } from "./MapCanvas";

interface VectorMapProps {
  points: MapPointView[];
  /** True if the API only returned the newest items. */
  truncated: boolean;
  onOpen: (itemId: string) => void;
}

/** 2D map of the items (hand-made SVG): zoom from 1 to 8, keyboard points, type legend. */
export function VectorMap({ points, truncated, onOpen }: VectorMapProps) {
  if (points.length === 0) return <EmptyState title={t("memory.map.empty")} />;
  return (
    <div className="flex flex-col gap-3">
      <MapCanvas points={points} onOpen={onOpen} />
      {truncated ? (
        <p className="text-sm text-muted-foreground">{t("memory.map.truncated")}</p>
      ) : null}
      <ul aria-label={t("memory.map.legend")} className="flex flex-wrap gap-x-4 gap-y-1">
        {MEMORY_KINDS.map((kind) => (
          <li key={kind}>
            <KindBadge kind={kind} />
          </li>
        ))}
      </ul>
    </div>
  );
}
