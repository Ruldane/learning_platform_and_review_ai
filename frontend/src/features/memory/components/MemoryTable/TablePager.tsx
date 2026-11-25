import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface TablePagerProps {
  total: number;
  offset: number;
  limit: number;
  /** Number of items shown on the current page. */
  shown: number;
  onPage: (offset: number) => void;
}

/** Offset pagination: displayed range, previous and next. */
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
