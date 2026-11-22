import { t } from "@/shared/i18n/t";
import type { MemoryItemDetailView } from "../viewTypes";

export function LinkedNotes({ notes, onOpenItem }: {
  notes: MemoryItemDetailView["linkedNotes"];
  onOpenItem: (id: string) => void;
}) {
  if (notes.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold">{t("memory.drawer.linkedNotes")}</h3>
      <ul className="flex flex-col gap-1 text-sm">
        {notes.map(({ itemId, title }) => (
          <li key={itemId}>
            <button type="button" onClick={() => onOpenItem(itemId)} className="text-left underline underline-offset-4">
              {title}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
