import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { MemoryItemDrawer } from "../../components/MemoryItemDrawer";
import type { ItemEdit, NewItem } from "../../components/viewTypes";
import { useItemMutations } from "../../hooks/useItemMutations";
import { useMemoryItem } from "../../hooks/useMemoryItem";

interface ItemPanelProps {
  /** Élément ouvert (`?item=`) ; `null` : aucun. */
  itemId: string | null;
  /** Tiroir en création (bouton « Ajouter »). */
  creating: boolean;
  onClose: () => void;
  onOpenItem: (id: string) => void;
}

/** Tiroir de détail, de modification et de création ; chargement et échec du détail en place. */
export function ItemPanel({ itemId, creating, onClose, onOpenItem }: ItemPanelProps) {
  const detail = useMemoryItem(creating ? null : itemId);
  const { create, update, remove } = useItemMutations();
  const writes = [create, update, remove];
  const failure = writes.find((write) => write.isError)?.error ?? null;

  const save = (value: ItemEdit | NewItem) => {
    if ("kind" in value) create.mutate(value, { onSuccess: (created) => onOpenItem(created.id) });
    else if (itemId) update.mutate({ id: itemId, value });
  };

  if (!creating && itemId === null) return null;
  if (!creating && detail.isError) {
    const gone = detail.error instanceof ApiError && detail.error.code === "memory_item_not_found";
    return (
      <ErrorState
        message={errorMessage(detail.error)}
        onRetry={gone ? onClose : () => void detail.refetch()}
        actionLabel={gone ? t("memory.button.close") : undefined}
      />
    );
  }
  if (!creating && !detail.data) return <LoadingState label={t("memory.page.loadingItem")} />;
  return (
    <MemoryItemDrawer
      open
      item={creating ? null : (detail.data ?? null)}
      busy={writes.some((write) => write.isPending)}
      error={failure ? errorMessage(failure) : null}
      onClose={onClose}
      onSave={save}
      onDelete={(id) => remove.mutate(id, { onSuccess: onClose })}
      onOpenItem={onOpenItem}
    />
  );
}
