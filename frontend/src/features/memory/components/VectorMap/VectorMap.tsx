import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { MEMORY_KINDS } from "../kindColors";
import { KindBadge } from "../KindBadge";
import type { MapPointView } from "../viewTypes";
import { MapCanvas } from "./MapCanvas";

interface VectorMapProps {
  points: MapPointView[];
  /** Vrai si l'API n'a rendu que les éléments les plus récents. */
  truncated: boolean;
  onOpen: (itemId: string) => void;
}

/** Carte 2D des éléments (SVG fait main) : zoom de 1 à 8, points au clavier, légende des types. */
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
