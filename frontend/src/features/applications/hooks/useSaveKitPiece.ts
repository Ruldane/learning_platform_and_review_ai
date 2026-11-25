import { useMutation, useQueryClient } from "@tanstack/react-query";
import { patchKitItem } from "../api";
import { kitSaveErrorMessage } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { KitItemOut, KitKindView, KitOut, KitSaveResult } from "../types";

const replaced = (kit: KitOut | undefined, item: KitItemOut): KitOut | undefined =>
  kit && { ...kit, items: kit.items.map((old) => (old.kind === item.kind ? item : old)) };

/**
 * Saves January's text for a piece: the server returns the re-read piece (status, terms),
 * which replaces the cached one. A change never waits for a running kit to finish.
 * Never throws: a refusal is a `KitSaveResult` to show under the piece.
 */
export function useSaveKitPiece(applicationId: string) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ kind, content }: { kind: KitKindView; content: string }) =>
      patchKitItem(applicationId, kind, content),
    onSuccess: (item) =>
      client.setQueryData<KitOut>(applicationsKeys.kit(applicationId), (kit) =>
        replaced(kit, item),
      ),
  });
  const { mutateAsync } = mutation;
  return (kind: KitKindView, content: string): Promise<KitSaveResult> =>
    mutateAsync({ kind, content }).then(
      (item): KitSaveResult => ({ ok: true, status: item.status }),
      (error: unknown): KitSaveResult => ({ ok: false, message: kitSaveErrorMessage(error) }),
    );
}
