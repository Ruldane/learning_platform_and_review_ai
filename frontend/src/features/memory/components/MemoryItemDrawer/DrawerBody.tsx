import { useState } from "react";
import { MemoryItemForm } from "../MemoryItemForm";
import type { ItemEdit, ItemPatch, MemoryItemDetailView, NewItem } from "../viewTypes";
import { ChunkList } from "./ChunkList";
import { ItemActions } from "./ItemActions";
import { ItemDetails } from "./ItemDetails";
import { LinkedNotes } from "./LinkedNotes";
import { NeighborList } from "./NeighborList";
import { WriteJournal } from "./WriteJournal";

interface DrawerBodyProps {
  item: MemoryItemDetailView | null;
  busy: boolean;
  onClose: () => void;
  onSave: (value: ItemPatch | NewItem) => void;
  onDelete: (id: string) => void;
  onOpenItem: (id: string) => void;
}

/** Only the « déclaré » and « en cours » levels are edited by hand (SPEC 4.2). */
function toEdit(item: MemoryItemDetailView): ItemEdit {
  const level = item.level === "declared" || item.level === "in_progress" ? item.level : null;
  return { title: item.title, text: item.text, tags: item.tags, level };
}

/** Drawer content: create form, detail view, or edit form. */
export function DrawerBody({ item, busy, onClose, onSave, onDelete, onOpenItem }: DrawerBodyProps) {
  // We keep the item being edited: once the detail is re-read after saving,
  // it is a new object and reading resumes on its own; a save in error keeps the form.
  const [editedItem, setEditedItem] = useState<MemoryItemDetailView | null>(null);

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
        // A document's text is the full extracted text: we do not edit it here.
        withText={item.kind !== "document"}
        disabled={busy}
        onSubmit={onSave}
        onCancel={() => setEditedItem(null)}
      />
    );
  }
  return (
    <>
      <ItemDetails item={item} />
      <ItemActions
        busy={busy}
        onEdit={() => setEditedItem(item)}
        onDelete={() => onDelete(item.id)}
      />
      <ChunkList chunks={item.chunks} />
      <LinkedNotes notes={item.linkedNotes} onOpenItem={onOpenItem} />
      <NeighborList neighbors={item.neighbors} onOpenItem={onOpenItem} />
      <WriteJournal writes={item.writes} />
    </>
  );
}
