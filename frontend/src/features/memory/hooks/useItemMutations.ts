import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { createItem, deleteItem, mergeItems, patchItem } from "../api";
import { memoryKeys } from "../queryKeys";
import type { ItemPatch, NewItem } from "../types";

/**
 * Any write changes the list, the statistics and the map (and an open detail): everything is
 * re-read. Deleted or merged items (`gone`) are not re-read: a detail left open does not
 * show a spurious 404 before the drawer closes.
 */
export function invalidateMemory(queryClient: QueryClient, gone: string[] = []) {
  return queryClient.invalidateQueries({
    queryKey: memoryKeys.all,
    predicate: ({ queryKey }) => !(queryKey[1] === "item" && gone.includes(String(queryKey[2]))),
  });
}

/** A write mutation; `gone` names the items that no longer exist after success. */
function useWrite<V, R>(run: (variables: V) => Promise<R>, gone?: (variables: V) => string[]) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: run,
    onSuccess: (_result, variables) => invalidateMemory(queryClient, gone?.(variables)),
  });
}

/**
 * Explorer writes: create, edit, delete, confirm or refuse a pending decision
 * (PATCH `status: "active"` / DELETE), merge. Each success invalidates `items`, `stats`,
 * `map` (and the documents, and the open detail).
 */
export function useItemMutations() {
  return {
    create: useWrite((value: NewItem) => createItem(value)),
    update: useWrite(({ id, value }: { id: string; value: ItemPatch }) => patchItem(id, value)),
    remove: useWrite(
      (id: string) => deleteItem(id),
      (id) => [id],
    ),
    confirm: useWrite((id: string) => patchItem(id, { status: "active" })),
    reject: useWrite(
      (id: string) => deleteItem(id),
      (id) => [id],
    ),
    merge: useWrite(
      ({ id, otherIds }: { id: string; otherIds: string[] }) => mergeItems(id, otherIds),
      ({ otherIds }) => otherIds,
    ),
  };
}
