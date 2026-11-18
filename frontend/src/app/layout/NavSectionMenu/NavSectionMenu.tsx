import { t } from "@/shared/i18n/t";
import type { NavGroup } from "../../buildNav";
import type { CurrentNav } from "../../navActive";
import { NavMenuLink } from "../NavMenuLink";
import { SectionButton } from "./SectionButton";
import { useSectionMenu } from "./useSectionMenu";

interface NavSectionMenuProps {
  group: NavGroup;
  current: CurrentNav | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Une section à plusieurs pages : un bouton qui ouvre un sous-menu (voir `useSectionMenu`). */
export function NavSectionMenu({ group, current, open, onOpenChange }: NavSectionMenuProps) {
  const { wrapRef, buttonRef, menuRef, close, onButtonKey, onMenuKey, onWrapKey, onWrapBlur } =
    useSectionMenu(open, onOpenChange);
  return (
    <div
      ref={wrapRef}
      className="relative"
      onKeyDown={onWrapKey}
      onBlur={onWrapBlur}
    >
      <SectionButton
        ref={buttonRef}
        group={group}
        active={current?.section === group.section}
        open={open}
        onToggle={() => onOpenChange(!open)}
        onKeyDown={onButtonKey}
      />
      {open ? (
        <ul
          ref={menuRef}
          role="menu"
          aria-label={t(group.labelKey)}
          onKeyDown={onMenuKey}
          className="absolute left-0 top-full z-20 mt-1 flex min-w-48 flex-col gap-1 rounded-lg border border-border bg-card p-1 shadow-md"
        >
          {group.items.map((item) => (
            <li key={item.path} role="none">
              <NavMenuLink
                item={item}
                color={group.color}
                role="menuitem"
                active={current?.path === item.path}
                onNavigate={close}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
