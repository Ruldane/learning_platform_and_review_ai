import type { ReactNode } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { ShellSlots } from "../Shell";

interface TopbarProps {
  /** Le voyant de santé, à droite du nom ; absent sur une page nue. */
  health?: ReactNode;
  /** Les menus de navigation ; absents sur une page nue (le nom n'y est alors pas un lien). */
  menus?: ReactNode;
}

/**
 * Barre du haut : à gauche le nom de l'application (lien vers l'accueil) et le voyant de santé,
 * puis les menus (sur deux lignes au besoin), à droite les emplacements `topbar` des features.
 */
export function Topbar({ health, menus }: TopbarProps) {
  return (
    <header className="flex flex-wrap items-start gap-x-4 gap-y-1 border-b border-border bg-card px-4 py-2">
      <div className="flex shrink-0 items-center gap-3 py-2">
        {menus ? (
          <Link to="/" className="font-semibold">
            {t("app.name")}
          </Link>
        ) : (
          <span className="font-semibold">{t("app.name")}</span>
        )}
        {health}
      </div>
      {menus}
      <div className="ml-auto flex items-center gap-4 py-2">
        <ShellSlots slot="topbar" />
      </div>
    </header>
  );
}
