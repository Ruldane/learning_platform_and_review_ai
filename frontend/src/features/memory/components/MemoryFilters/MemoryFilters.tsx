import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { ItemFilterValue } from "../viewTypes";
import { KindAuthorSelects } from "./KindAuthorSelects";

interface MemoryFiltersProps {
  value: ItemFilterValue;
  authors: string[];
  onChange: (value: ItemFilterValue) => void;
}

const labelClass = "flex flex-col gap-1 text-sm font-medium";

/** Filtres de la liste : type, étiquette, auteur et bornes de date. */
export function MemoryFilters({ value, authors, onChange }: MemoryFiltersProps) {
  const set = (patch: Partial<ItemFilterValue>) => onChange({ ...value, ...patch });
  return (
    <div
      role="group"
      aria-label={t("memory.filters.label")}
      className="flex flex-wrap items-end gap-3"
    >
      <KindAuthorSelects value={value} authors={authors} onChange={set} />
      <label className={labelClass}>
        {t("memory.filters.tag")}
        <input
          type="text"
          value={value.tag}
          onChange={(e) => set({ tag: e.target.value })}
          className={fieldClass}
        />
      </label>
      <label className={labelClass}>
        {t("memory.filters.since")}
        <input
          type="date"
          value={value.since}
          onChange={(e) => set({ since: e.target.value })}
          className={fieldClass}
        />
      </label>
      <label className={labelClass}>
        {t("memory.filters.until")}
        <input
          type="date"
          value={value.until}
          onChange={(e) => set({ until: e.target.value })}
          className={fieldClass}
        />
      </label>
    </div>
  );
}
