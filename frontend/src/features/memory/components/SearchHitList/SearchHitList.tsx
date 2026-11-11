import { t } from "@/shared/i18n/t";
import { authorLabel } from "../authorLabel";
import { formatScore } from "../formatScore";
import { KindBadge } from "../KindBadge";
import type { SearchHitView } from "../viewTypes";

interface SearchHitListProps {
  hits: SearchHitView[];
  /** Absent (banc d'essai) : le titre reste un simple texte. */
  onOpen?: (itemId: string) => void;
}

/** Fragments trouvés, avec le type, l'auteur, un extrait et le score de similarité. */
export function SearchHitList({ hits, onOpen }: SearchHitListProps) {
  if (hits.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("memory.search.noResults")}</p>;
  }
  return (
    <ul aria-label={t("memory.search.hits")} className="flex flex-col gap-2">
      {hits.map((hit) => (
        <li key={hit.chunk_id} className="rounded-lg border border-border bg-card px-3 py-2">
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <KindBadge kind={hit.kind} />
              {onOpen ? (
                <button
                  type="button"
                  onClick={() => onOpen(hit.item_id)}
                  className="text-left font-medium underline-offset-4 hover:underline focus-visible:underline"
                >
                  {hit.title}
                </button>
              ) : (
                <span className="font-medium">{hit.title}</span>
              )}
              <span className="text-xs text-muted-foreground">{authorLabel(hit.created_by)}</span>
            </div>
            <span className="text-sm tabular-nums">
              <span className="sr-only">{t("memory.search.score")} </span>
              <span>{formatScore(hit.score)}</span>
            </span>
          </div>
          <p className="mt-1 line-clamp-3 text-sm text-muted-foreground">{hit.text}</p>
        </li>
      ))}
    </ul>
  );
}
