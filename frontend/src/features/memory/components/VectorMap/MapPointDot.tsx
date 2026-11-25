import { t } from "@/shared/i18n/t";
import { KIND_COLORS } from "../kindColors";
import type { MapPointView } from "../viewTypes";

/** Radius of a point, in map units, at zoom 1 (divided by the zoom: fixed screen size). */
const POINT_RADIUS = 0.02;
const STROKE = 0.006;

interface MapPointDotProps {
  point: MapPointView;
  zoom: number;
  /** Called on click; the parent ignores clicks that end a drag. */
  onClick: () => void;
  onActivate: () => void;
  onFocus: () => void;
}

/** A map item: a circle in its type's colour, reachable and activatable by keyboard. */
export function MapPointDot({ point, zoom, onClick, onActivate, onFocus }: MapPointDotProps) {
  const kind = t(`memory.kind.${point.kind}`);
  return (
    <circle
      role="button"
      tabIndex={0}
      aria-label={t("memory.map.point", { title: point.title, kind })}
      cx={point.x}
      cy={point.y}
      r={POINT_RADIUS / zoom}
      fill={KIND_COLORS[point.kind]}
      strokeWidth={STROKE / zoom}
      className="cursor-pointer stroke-background outline-none hover:stroke-foreground focus-visible:stroke-foreground motion-safe:transition-[stroke] motion-safe:duration-150"
      onClick={onClick}
      onFocus={onFocus}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onActivate();
        }
      }}
    >
      <title>{point.title}</title>
    </circle>
  );
}
