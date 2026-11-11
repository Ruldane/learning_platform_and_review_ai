import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { createItem, deleteItem, mergeItems, patchItem } from "../api";
import { memoryKeys } from "../queryKeys";
import type { ItemPatch, NewItem } from "../types";

/**
 * Toute écriture change la liste, les statistiques et la carte (et un détail ouvert) : tout est
 * relu. Les éléments supprimés ou fondus (`gone`) ne sont pas relus : un détail resté ouvert ne
 * montre pas un 404 parasite avant la fermeture du tiroir.
 */
export function invalidateMemory(queryClient: QueryClient, gone: string[] = []) {
  return queryClient.invalidateQueries({
    queryKey: memoryKeys.all,
    predicate: ({ queryKey }) => !(queryKey[1] === "item" && gone.includes(String(queryKey[2]))),
  });
}

/** Une mutation d'écriture ; `gone` désigne les éléments qui n'existent plus après le succès. */
function useWrite<V, R>(run: (variables: V) => Promise<R>, gone?: (variables: V) => string[]) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: run,
    onSuccess: (_result, variables) => invalidateMemory(queryClient, gone?.(variables)),
  });
}

/**
 * Écritures de l'explorateur : créer, modifier, supprimer, confirmer ou refuser une décision en
 * attente (PATCH `status: "active"` / DELETE), fusionner. Chaque succès invalide `items`, `stats`,
 * `map` (et les documents, le détail ouvert).
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
