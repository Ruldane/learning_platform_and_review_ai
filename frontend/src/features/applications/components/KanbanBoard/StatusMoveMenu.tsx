import { ArrowRightLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { StatusView } from "../viewTypes";
import { StatusMoveMenuList } from "./StatusMoveMenuList";

interface StatusMoveMenuProps {
  title: string;
  company: string;
  current: StatusView;
  onSelect: (status: StatusView) => void;
}

/** Menu « Déplacer vers… » : l'équivalent au clavier du glisser-déposer, un statut par entrée. */
export function StatusMoveMenu({ title, company, current, onSelect }: StatusMoveMenuProps) {
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
        aria-label={t("applications.board.moveButton", { title, company })}
        title={t("applications.board.moveTo")}
        onClick={() => setOpen((value) => !value)}
      >
        <ArrowRightLeft aria-hidden="true" />
      </Button>
      {open && <StatusMoveMenuList current={current} onSelect={onSelect} onClose={close} />}
    </div>
  );
}
