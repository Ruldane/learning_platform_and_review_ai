import { ArrowRightLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { MoveMenuList } from "./MoveMenuList";

interface MoveMenuProps {
  taskTitle: string;
  /** Jours proposés (`AAAA-MM-JJ`), hors celui où se trouve déjà la tâche. */
  dates: string[];
  onSelect: (date: string) => void;
}

/** Menu « Déplacer vers… » : l'équivalent au clavier du glisser-déposer. */
export function MoveMenu({ taskTitle, dates, onSelect }: MoveMenuProps) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
    function onPointerDown(event: MouseEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  function close(refocus: boolean) {
    setOpen(false);
    if (refocus) trigger.current?.focus();
  }

  return (
    <div ref={root} className="relative">
      <Button
        ref={trigger}
        type="button"
        variant="ghost"
        size="icon-xs"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("program.calendar.move", { title: taskTitle })}
        title={t("program.calendar.moveTo")}
        onClick={() => setOpen((value) => !value)}
      >
        <ArrowRightLeft aria-hidden="true" />
      </Button>
      {open && <MoveMenuList dates={dates} onSelect={onSelect} onClose={close} />}
    </div>
  );
}
