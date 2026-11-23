import { t } from "@/shared/i18n/t";
import type { NavGroup } from "../../buildNav";
import type { CurrentNav } from "../../navActive";
import { NavMenuLink } from "../NavMenuLink";

interface NavMobileSectionProps {
  group: NavGroup;
  current: CurrentNav | null;
  onClose: () => void;
}

/** Une section dans le panneau « Menu » : un lien direct (une page) ou un titre et ses pages. */
export function NavMobileSection({ group, current, onClose }: NavMobileSectionProps) {
  const Icon = group.icon;
  const single = group.landing ?? (group.items.length === 1 ? group.items[0] : undefined);
  if (single) {
    return (
      <NavMenuLink
        item={single}
        color={group.color}
        icon={Icon}
        badgeItems={group.landing ? group.items : undefined}
        active={current?.section === group.section}
        current={current?.path === single.path ? "page" : current?.section === group.section ? "location" : undefined}
        onNavigate={onClose}
      />
    );
  }
  return (
    <div>
      <h2 className="flex items-center gap-2 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <Icon aria-hidden="true" className="size-4" />
        {t(group.labelKey)}
      </h2>
      <ul className="flex flex-col gap-1">
        {group.items.map((item) => (
          <li key={item.path}>
            <NavMenuLink
              item={item}
              color={group.color}
              active={current?.path === item.path}
              onNavigate={onClose}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
