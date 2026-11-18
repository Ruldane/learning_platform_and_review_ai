import type { ReactNode } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { NavGroup } from "../../buildNav";
import { ShellSlots } from "../Shell";
import { WhereAmI } from "./WhereAmI";

interface InfoPanelProps {
  groups: NavGroup[];
  /** Le voyant de santé. */
  health: ReactNode;
  /** Écran étroit : une ligne compacte sous la barre, au lieu du panneau de gauche. */
  compact?: boolean;
}

/**
 * Le panneau de gauche : le nom (lien vers l'accueil), « Tu es ici », le voyant de santé, puis ce
 * que les features déclarent dans leur emplacement `topbar` (série, heures, capture, compte…), une
 * info par ligne. Fixe sous la barre ; sous 1024 px, une ligne compacte (voir `AppLayout`).
 *
 * C'est ici que l'emplacement `topbar` est rendu : le nom de l'emplacement ne change pas, les
 * features n'ont donc pas à être retouchées quand on le redirige.
 */
export function InfoPanel({ groups, health, compact = false }: InfoPanelProps) {
  return (
    <aside
      aria-label={t("nav.panel")}
      className={cn(
        "bg-card",
        compact ? "border-b border-border px-4 py-2" : "w-60 shrink-0 border-r border-border",
      )}
    >
      <div
        className={cn(
          compact
            ? "flex flex-wrap items-center gap-x-6 gap-y-2"
            : "sticky top-0 flex max-h-screen flex-col items-start gap-4 overflow-y-auto p-4 [&_ul]:flex-col [&_ul]:items-start [&_ul]:gap-2",
        )}
      >
        <Link to="/" className="text-lg font-semibold">
          {t("app.name")}
        </Link>
        <WhereAmI groups={groups} compact={compact} />
        {health}
        <ShellSlots slot="topbar" />
      </div>
    </aside>
  );
}
