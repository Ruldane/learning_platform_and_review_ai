import { useMutation, useQueryClient } from "@tanstack/react-query";
import { patchKitItem } from "../api";
import { kitSaveErrorMessage } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { KitItemOut, KitKindView, KitOut, KitSaveResult } from "../types";

const replaced = (kit: KitOut | undefined, item: KitItemOut): KitOut | undefined =>
  kit && { ...kit, items: kit.items.map((old) => (old.kind === item.kind ? item : old)) };

/**
 * Enregistre le texte de January pour une pièce : le serveur rend la pièce relue (statut, termes),
 * qui remplace celle du kit en cache. Une modification n'attend jamais la fin d'un kit en cours.
 * Ne lève pas : un refus est un `KitSaveResult` à montrer sous la pièce.
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
