import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { MemoryItemForm } from "../MemoryItemForm";
import type { ItemEdit, MemoryItemDetailView, NewItem } from "../viewTypes";
import { ChunkList } from "./ChunkList";
import { DeleteConfirm } from "./DeleteConfirm";
import { ItemDetails } from "./ItemDetails";
import { NeighborList } from "./NeighborList";
import { WriteJournal } from "./WriteJournal";

interface DrawerBodyProps {
  item: MemoryItemDetailView | null;
  busy: boolean;
  onClose: () => void;
  onSave: (value: ItemEdit | NewItem) => void;
  onDelete: (id: string) => void;
  onOpenItem: (id: string) => void;
}

/** Seuls les niveaux « déclaré » et « en cours » se modifient à la main (SPEC 4.2). */
function toEdit(item: MemoryItemDetailView): ItemEdit {
  const level = item.level === "declare" || item.level === "en_cours" ? item.level : null;
  return { title: item.title, text: item.text, tags: item.tags, level };
}

/** Contenu du tiroir : formulaire de création, lecture du détail ou formulaire de modification. */
export function DrawerBody({ item, busy, onClose, onSave, onDelete, onOpenItem }: DrawerBodyProps) {
  // On retient l'objet en cours de modification : une fois le détail relu après l'enregistrement,
  // c'est un nouvel objet et la lecture reprend seule ; une sauvegarde en erreur garde le formulaire.
  const [editedItem, setEditedItem] = useState<MemoryItemDetailView | null>(null);
  const [confirming, setConfirming] = useState(false);

  if (item === null) {
    return (
      <MemoryItemForm
        initial={null}
        chooseKind
        disabled={busy}
        onSubmit={onSave}
        onCancel={onClose}
      />
    );
  }
  if (editedItem === item) {
    return (
      <MemoryItemForm
        initial={toEdit(item)}
        chooseKind={false}
        disabled={busy}
        onSubmit={onSave}
        onCancel={() => setEditedItem(null)}
      />
    );
  }
  return (
    <>
      <ItemDetails item={item} />
      {confirming ? (
        <DeleteConfirm
          busy={busy}
          onConfirm={() => onDelete(item.id)}
          onKeep={() => setConfirming(false)}
        />
      ) : (
        <div className="flex gap-2">
          <Button variant="outline" disabled={busy} onClick={() => setEditedItem(item)}>
            {t("memory.button.edit")}
          </Button>
          <Button variant="destructive" disabled={busy} onClick={() => setConfirming(true)}>
            {t("memory.button.delete")}
          </Button>
        </div>
      )}
      <ChunkList chunks={item.chunks} />
      <NeighborList neighbors={item.neighbors} onOpenItem={onOpenItem} />
      <WriteJournal writes={item.writes} />
    </>
  );
}
