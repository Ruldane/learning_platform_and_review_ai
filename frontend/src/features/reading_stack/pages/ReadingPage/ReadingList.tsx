import { NavLink } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ReadingItem } from "../../api";

export const READING_PATH = "/memoire/lecture";

interface ReadingListProps {
  items: ReadingItem[];
  offset: number;
  next: number | null;
  onPage: (offset: number) => void;
}

export function ReadingList({ items, offset, next, onPage }: ReadingListProps) {
  return (
    <section aria-label={t("reading.list")} className="flex min-w-0 flex-col gap-3">
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("reading.empty")}</p>
      ) : null}
      <ul className="divide-y rounded-xl border bg-card">
        {items.map((item) => (
          <li key={item.id} className="p-3">
            <p className="text-xs text-muted-foreground">{t(`reading.kind.${item.kind}`)}</p>
            <NavLink
              className="block break-words font-medium underline-offset-4 hover:underline aria-[current=page]:underline"
              to={`${READING_PATH}/${item.id}`}
            >
              {item.title}
            </NavLink>
            {item.summary ? (
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{item.summary}</p>
            ) : null}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        {offset > 0 ? (
          <Button variant="outline" onClick={() => onPage(Math.max(0, offset - 50))}>
            {t("reading.earlier")}
          </Button>
        ) : null}
        {next !== null ? (
          <Button variant="outline" onClick={() => onPage(next)}>
            {t("reading.more")}
          </Button>
        ) : null}
      </div>
    </section>
  );
}
