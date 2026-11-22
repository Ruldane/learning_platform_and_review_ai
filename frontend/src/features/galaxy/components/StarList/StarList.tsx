import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { Star } from "../GalaxyCanvas/projection";

interface StarListProps {
  stars: Star[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export function StarList({ stars, selected, onSelect }: StarListProps) {
  const [filter, setFilter] = useState("");
  const query = filter.trim().toLocaleLowerCase("fr");
  const visible = stars.filter((star) => star.title.toLocaleLowerCase("fr").includes(query));
  return (
    <section aria-labelledby="galaxy-list" className="flex min-w-0 flex-col gap-2">
      <h2 id="galaxy-list" className="text-lg font-semibold">
        {t("galaxy.list")}
      </h2>
      <label className="flex flex-col gap-1 text-sm">
        {t("galaxy.filter")}
        <input
          type="search"
          className={fieldClass}
          value={filter}
          onChange={(event) => setFilter(event.currentTarget.value)}
        />
      </label>
      {visible.length === 0 && <p role="status">{t("galaxy.noMatch")}</p>}
      <ul className="max-h-64 overflow-y-auto rounded-lg border border-border p-1">
        {visible.map((star) => (
          <li key={star.id}>
            <Button
              variant={selected === star.id ? "secondary" : "ghost"}
              aria-pressed={selected === star.id}
              aria-label={`${star.title} ${t(`galaxy.${star.kind}`)}`}
              onClick={() => onSelect(star.id)}
              className="h-auto w-full justify-between whitespace-normal py-2 text-left"
            >
              <span className="min-w-0 wrap-break-word">{star.title}</span>
              <span className="text-xs text-muted-foreground">{t(`galaxy.${star.kind}`)}</span>
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
