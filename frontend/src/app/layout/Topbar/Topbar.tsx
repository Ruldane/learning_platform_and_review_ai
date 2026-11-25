import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { ShellSlots } from "../Shell";

interface TopbarProps {
  /**
   * Navigation menus, centered in the bar. Absent on a bare page: the bar then keeps
   * the name (as plain text) and the `topbar` slots of features (account,
   * sign-out), since the left panel is not there.
   */
  menus?: ReactNode;
}

/** Top bar: menus in the center; the rest lives in the left panel (`InfoPanel`). */
export function Topbar({ menus }: TopbarProps) {
  if (menus) {
    return (
      <header className="flex items-start justify-center border-b border-border bg-card px-4 py-2">
        {menus}
      </header>
    );
  }
  return (
    <header className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-border bg-card px-4 py-2">
      <span className="py-2 font-semibold">{t("app.name")}</span>
      <div className="ml-auto flex items-center gap-4 py-2">
        <ShellSlots slot="topbar" />
      </div>
    </header>
  );
}
