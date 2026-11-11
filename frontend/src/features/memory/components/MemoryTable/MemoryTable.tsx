import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { MemoryFilters } from "../MemoryFilters";
import type { ItemFilterValue, MemoryItemRow } from "../viewTypes";
import { ItemsTable } from "./ItemsTable";
import { MergeBar } from "./MergeBar";
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
  /** Fusion en cours : bouton et sélection verrouillés. */
  merging: boolean;
}

/** Liste des éléments de mémoire : filtres, sélection, fusion et pagination (présentationnel). */
export function MemoryTable(props: MemoryTableProps) {
  const { items, total, offset, limit, selected, merging, onSelect } = props;
  const pager = (
    <TablePager
      total={total}
      offset={offset}
      limit={limit}
      shown={items.length}
      onPage={props.onPage}
    />
  );

  return (
    <div className="flex flex-col gap-4">
      <MemoryFilters
        value={props.filters}
        authors={props.authors}
        onChange={props.onFiltersChange}
      />
      {items.length === 0 ? (
        <>
          <EmptyState title={t("memory.empty")} />
          {total > limit ? pager : null}
        </>
      ) : (
        <>
          <ItemsTable
            items={items}
            selected={selected}
            locked={merging}
            onToggle={(id) =>
              onSelect(
                selected.includes(id)
                  ? selected.filter((other) => other !== id)
                  : [...selected, id],
              )
            }
            onOpen={props.onOpen}
          />
          <div className="flex flex-wrap items-start justify-between gap-3">
            <MergeBar items={items} selected={selected} merging={merging} onMerge={props.onMerge} />
            {pager}
          </div>
        </>
      )}
    </div>
  );
}
