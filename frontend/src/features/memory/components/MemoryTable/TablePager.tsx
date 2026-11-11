import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface TablePagerProps {
  total: number;
  offset: number;
  limit: number;
  /** Nombre d'éléments affichés sur la page courante. */
  shown: number;
  onPage: (offset: number) => void;
}

/** Pagination par décalage : plage affichée, précédent et suivant. */
export function TablePager({ total, offset, limit, shown, onPage }: TablePagerProps) {
  const range = t("memory.table.range", { from: offset + 1, to: offset + shown, total });
  return (
    <nav aria-label={t("memory.table.caption")} className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">{range}</span>
      <Button
        variant="outline"
        size="sm"
        disabled={offset <= 0}
        onClick={() => onPage(Math.max(0, offset - limit))}
      >
        {t("memory.button.previous")}
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled={offset + limit >= total}
        onClick={() => onPage(offset + limit)}
      >
        {t("memory.button.next")}
      </Button>
    </nav>
  );
}
