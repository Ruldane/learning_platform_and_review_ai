import { t } from "@/shared/i18n/t";
import { KIND_COLORS } from "../kindColors";
import type { MapPointView } from "../viewTypes";

/** Rayon d'un point, en unités de carte, au zoom 1 (il est divisé par le zoom : taille d'écran fixe). */
const POINT_RADIUS = 0.02;
const STROKE = 0.006;

interface MapPointDotProps {
  point: MapPointView;
  zoom: number;
  /** Appelée au clic ; le parent ignore les clics qui terminent un glissement. */
  onClick: () => void;
  onActivate: () => void;
  onFocus: () => void;
}

/** Un élément sur la carte : cercle de la couleur de son type, atteignable et activable au clavier. */
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
