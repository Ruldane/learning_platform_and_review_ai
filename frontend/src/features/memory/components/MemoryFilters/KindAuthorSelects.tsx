import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { authorLabel } from "../authorLabel";
import { MEMORY_KINDS } from "../kindColors";
import type { ItemFilterValue, MemoryKindView } from "../viewTypes";

interface KindAuthorSelectsProps {
  value: ItemFilterValue;
  authors: string[];
  onChange: (patch: Partial<ItemFilterValue>) => void;
}

const labelClass = "flex flex-col gap-1 text-sm font-medium";

/** Listes déroulantes du type et de l'auteur. */
export function KindAuthorSelects({ value, authors, onChange }: KindAuthorSelectsProps) {
  const set = onChange;
  return (
    <>
      <label className={labelClass}>
        {t("memory.filters.kind")}
        <select
          value={value.kind}
          onChange={(e) => set({ kind: e.target.value as MemoryKindView | "" })}
          className={fieldClass}
        >
          <option value="">{t("memory.filters.allKinds")}</option>
          {MEMORY_KINDS.map((kind) => (
            <option key={kind} value={kind}>
              {t(`memory.kind.${kind}`)}
            </option>
          ))}
        </select>
      </label>
      <label className={labelClass}>
        {t("memory.filters.author")}
        <select
          value={value.author}
          onChange={(e) => set({ author: e.target.value })}
          className={fieldClass}
        >
          <option value="">{t("memory.filters.allAuthors")}</option>
          {authors.map((slug) => (
            <option key={slug} value={slug}>
              {authorLabel(slug)}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}
