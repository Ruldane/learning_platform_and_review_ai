import type { ReactNode } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { NavGroup } from "../../buildNav";
import { ShellSlots } from "../Shell";
import { WhereAmI } from "./WhereAmI";

interface InfoPanelProps {
  groups: NavGroup[];
  /** The health indicator. */
  health: ReactNode;
  /** Narrow screen: a compact line below the bar, instead of the left panel. */
  compact?: boolean;
}

/**
 * The left panel: the name (link to home), « Tu es ici », the health indicator, then what
 * features declare in their `topbar` slot (streak, hours, capture, account...), one
 * item per line. Fixed below the bar; below 1024 px, a compact line (see `AppLayout`).
 *
 * This is where the `topbar` slot is rendered: the slot name does not change, so
 * features need not be touched when it is redirected.
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
