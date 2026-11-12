import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { ShellSlots } from "../Shell";

/**
 * Barre du haut : nom de l'application à gauche ; à droite, les emplacements `topbar` des features
 * puis le contenu libre (`right`).
 */
export function Topbar({ right }: { right: ReactNode }) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-card px-4 py-2">
      <span className="font-semibold">{t("app.name")}</span>
      <div className="flex items-center gap-4">
        <ShellSlots slot="topbar" />
        {right}
      </div>
    </header>
  );
}
