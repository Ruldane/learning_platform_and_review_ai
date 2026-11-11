import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";

/** Barre du haut : nom de l'application à gauche, contenu libre (`right`) à droite. */
export function Topbar({ right }: { right: ReactNode }) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-card px-4 py-2">
      <span className="font-semibold">{t("app.name")}</span>
      <div>{right}</div>
    </header>
  );
}
