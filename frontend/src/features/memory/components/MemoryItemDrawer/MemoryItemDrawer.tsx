import { useEffect, useId, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { ItemPatch, MemoryItemDetailView, NewItem } from "../viewTypes";
import { DrawerBody } from "./DrawerBody";

interface MemoryItemDrawerProps {
  open: boolean;
  /** `null`: creating a new item. */
  item: MemoryItemDetailView | null;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (value: ItemPatch | NewItem) => void;
  onDelete: (id: string) => void;
  onOpenItem: (id: string) => void;
}

/**
 * Detail drawer, to the right of the list. A deliberately non-modal `role="dialog"`: the list
 * behind stays readable and usable. Focus lands on the title (for each item opened) and
 * Escape closes the drawer.
 */
export function MemoryItemDrawer({
  open,
  item,
  busy,
  error,
  onClose,
  ...actions
}: MemoryItemDrawerProps) {
  const titleId = useId();
  const titleRef = useRef<HTMLHeadingElement>(null);
  const itemId = item?.id;

  useEffect(() => {
    if (open) titleRef.current?.focus();
  }, [open, itemId]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented) onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <section
      role="dialog"
      aria-labelledby={titleId}
      className="fixed inset-y-0 right-0 z-40 flex w-full max-w-xl flex-col gap-4 overflow-y-auto border-l border-border bg-card p-5 shadow-lg"
    >
      <header className="flex items-start justify-between gap-3">
        <h2
          id={titleId}
          ref={titleRef}
          tabIndex={-1}
          className="text-lg font-semibold outline-none"
        >
          {item?.title ?? t("memory.drawer.newTitle")}
        </h2>
        <Button variant="outline" size="sm" onClick={onClose}>
          {t("memory.button.close")}
        </Button>
      </header>
      {error ? <InlineError message={error} /> : null}
      <DrawerBody key={itemId ?? "new"} item={item} busy={busy} onClose={onClose} {...actions} />
    </section>
  );
}
