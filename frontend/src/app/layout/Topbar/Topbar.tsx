import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { ShellSlots } from "../Shell";

interface TopbarProps {
  /**
   * Les menus de navigation, centrés dans la barre. Absents sur une page nue : la barre garde
   * alors le nom (en simple texte) et les emplacements `topbar` des features (compte,
   * déconnexion), car le panneau de gauche n'y est pas.
   */
  menus?: ReactNode;
}

/** Barre du haut : les menus au centre ; le reste vit dans le panneau de gauche (`InfoPanel`). */
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
