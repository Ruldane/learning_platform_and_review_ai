import { useLocation } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { NavGroup } from "../../buildNav";
import { currentNav } from "../../navActive";

/**
 * The « Tu es ici » block: the section badge, its name and the page (« Réglages › Coûts »; the
 * name alone for a single-page section). Nothing on a page outside the navigation.
 */
export function WhereAmI({ groups, compact }: { groups: NavGroup[]; compact: boolean }) {
  const { pathname } = useLocation();
  const current = currentNav(groups, pathname);
  const group = groups.find((candidate) => candidate.section === current?.section);
  const item = group?.items.find((candidate) => candidate.path === current?.path);
  if (!group || !item) return null;
  const section = t(group.labelKey);
  const page = t(item.labelKey);
  return (
    <div
      role="group"
      aria-label={t("nav.here")}
      data-section={group.section}
      className={cn("flex flex-col gap-0.5", compact ? "min-w-0" : null)}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {t("nav.here")}
      </p>
      <p className="flex items-center gap-2 text-sm font-medium">
        <span
          aria-hidden="true"
          data-testid="section-dot"
          style={{ backgroundColor: group.color }}
          className="size-2.5 shrink-0 rounded-full"
        />
        <span>{page === section ? section : t("nav.crumb", { section, page })}</span>
      </p>
    </div>
  );
}
