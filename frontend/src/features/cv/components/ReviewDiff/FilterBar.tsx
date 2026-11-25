import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ModificationView } from "../viewTypes";

export type Filter = "all" | "todo" | "confirm";

const FILTERS: { value: Filter; label: "all" | "todo" | "confirm" }[] = [
  { value: "all", label: "all" },
  { value: "todo", label: "todo" },
  { value: "confirm", label: "confirm" },
];

/** A change is « à décider » while it is proposed or waiting to be confirmed. */
export function matches(mod: ModificationView, filter: Filter): boolean {
  if (filter === "confirm") return mod.status === "to_confirm";
  if (filter === "todo") return mod.status === "proposed" || mod.status === "to_confirm";
  return true;
}

interface FilterBarProps {
  mods: ModificationView[];
  filter: Filter;
  onChange: (filter: Filter) => void;
}

/** The three filters, with the number of changes for each. */
export function FilterBar({ mods, filter, onChange }: FilterBarProps) {
  return (
    <div role="group" aria-label={t("cv.review.filters")} className="flex flex-wrap gap-2">
      {FILTERS.map(({ value, label }) => (
        <Button
          key={value}
          variant={filter === value ? "default" : "outline"}
          aria-pressed={filter === value}
          onClick={() => onChange(value)}
        >
          {t(`cv.review.${label}`, { count: mods.filter((mod) => matches(mod, value)).length })}
        </Button>
      ))}
    </div>
  );
}
