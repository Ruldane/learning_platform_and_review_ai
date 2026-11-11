import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { MemoryTable } from "../../components/MemoryTable";
import type { ItemFilterValue } from "../../components/viewTypes";
import { authorChoices, isPristine, NO_FILTERS } from "../../filters";
import { ImportEmptyState } from "../ImportEmptyState";
import { useItemMutations } from "../../hooks/useItemMutations";
import { useMemoryItems } from "../../hooks/useMemoryItems";

const PAGE_SIZE = 25;

/** Décalage de la dernière page non vide pour `total` éléments. */
export function lastPageOffset(total: number, limit: number): number {
  return Math.max(0, Math.ceil(total / limit) - 1) * limit;
}

/** Liste filtrable et paginée des éléments, avec la fusion de la sélection ; vide : on propose l'import. */
export function ListSection({ onOpen }: { onOpen: (id: string) => void }) {
  const [filters, setFilters] = useState<ItemFilterValue>(NO_FILTERS);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const list = useMemoryItems({ filters, status: "active", offset, limit: PAGE_SIZE });
  const { merge } = useItemMutations();
  // Une suppression ou une fusion peut vider la dernière page : on revient à la dernière page non vide.
  if (list.data && list.data.items.length === 0 && offset > 0) {
    setOffset(lastPageOffset(list.data.total, PAGE_SIZE));
  }
  const changeFilters = (value: ItemFilterValue) => {
    setFilters(value);
    setOffset(0);
    setSelected([]);
  };

  if (list.isError) {
    return <ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} />;
  }
  if (!list.data) return <LoadingState />;
  if (list.data.total === 0 && isPristine(filters)) {
    return <ImportEmptyState title={t("memory.empty")} />;
  }
  return (
    <div className="flex flex-col gap-3">
      <MemoryTable
        items={list.data.items}
        total={list.data.total}
        offset={offset}
        limit={PAGE_SIZE}
        filters={filters}
        authors={authorChoices(
          list.data.items.map((item) => item.created_by),
          filters.author,
        )}
        selected={selected}
        onFiltersChange={changeFilters}
        onSelect={setSelected}
        onOpen={onOpen}
        onMerge={(id, otherIds) =>
          merge.mutate({ id, otherIds }, { onSuccess: () => setSelected([]) })
        }
        onPage={setOffset}
        merging={merge.isPending}
      />
      {merge.isError ? <InlineError message={errorMessage(merge.error)} /> : null}
    </div>
  );
}
