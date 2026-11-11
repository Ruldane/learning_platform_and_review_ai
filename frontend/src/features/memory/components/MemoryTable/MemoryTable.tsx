import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { MemoryFilters } from "../MemoryFilters";
import type { ItemFilterValue, MemoryItemRow } from "../viewTypes";
import { canMerge } from "./mergeRule";
import { ItemsTable } from "./ItemsTable";
import { TablePager } from "./TablePager";

interface MemoryTableProps {
  items: MemoryItemRow[];
  total: number;
  offset: number;
  limit: number;
  filters: ItemFilterValue;
  authors: string[];
  selected: string[];
  onFiltersChange: (value: ItemFilterValue) => void;
  onSelect: (ids: string[]) => void;
  onOpen: (id: string) => void;
  onMerge: (targetId: string, otherIds: string[]) => void;
  onPage: (offset: number) => void;
}

/** Liste des éléments de mémoire : filtres, sélection, fusion et pagination (présentationnel). */
export function MemoryTable(props: MemoryTableProps) {
  const { items, total, offset, limit, selected, onSelect, onMerge } = props;
  const picked = selected.map((id) => items.find((item) => item.id === id));
  // Un élément coché sur une autre page n'a pas de type connu ici : pas de fusion à l'aveugle.
  const mergeable =
    picked.every((item) => item !== undefined) && canMerge(picked as MemoryItemRow[]);
  const toggle = (id: string) =>
    onSelect(selected.includes(id) ? selected.filter((other) => other !== id) : [...selected, id]);
  const merge = () => {
    const [target, ...others] = selected;
    if (target !== undefined) onMerge(target, others);
  };

  return (
    <div className="flex flex-col gap-4">
      <MemoryFilters
        value={props.filters}
        authors={props.authors}
        onChange={props.onFiltersChange}
      />
      {items.length === 0 ? (
        <EmptyState title={t("memory.empty")} />
      ) : (
        <>
          <ItemsTable items={items} selected={selected} onToggle={toggle} onOpen={props.onOpen} />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="outline" disabled={!mergeable} onClick={merge}>
                {t("memory.button.merge")}
              </Button>
              <p className="text-xs text-muted-foreground">{t("memory.table.mergeHint")}</p>
            </div>
            <TablePager
              total={total}
              offset={offset}
              limit={limit}
              shown={items.length}
              onPage={props.onPage}
            />
          </div>
        </>
      )}
    </div>
  );
}
