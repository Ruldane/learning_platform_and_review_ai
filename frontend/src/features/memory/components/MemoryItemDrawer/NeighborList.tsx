import { t } from "@/shared/i18n/t";
import { formatScore } from "../formatScore";
import { KindBadge } from "../KindBadge";
import type { MemoryItemDetailView } from "../viewTypes";

interface NeighborListProps {
  neighbors: MemoryItemDetailView["neighbors"];
  onOpenItem: (id: string) => void;
}

/** Éléments voisins par similarité ; un clic ouvre le voisin dans le tiroir. */
export function NeighborList({ neighbors, onOpenItem }: NeighborListProps) {
  if (neighbors.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold">{t("memory.drawer.neighbors")}</h3>
      <ul className="flex flex-col gap-1">
        {neighbors.map((neighbor) => (
          <li key={neighbor.item_id} className="flex items-center justify-between gap-3 text-sm">
            <button
              type="button"
              onClick={() => onOpenItem(neighbor.item_id)}
              className="text-left underline-offset-4 hover:underline focus-visible:underline"
            >
              {neighbor.title}
            </button>
            <span className="flex items-center gap-3">
              <KindBadge kind={neighbor.kind} />
              <span className="tabular-nums text-muted-foreground">
                {formatScore(neighbor.score)}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
