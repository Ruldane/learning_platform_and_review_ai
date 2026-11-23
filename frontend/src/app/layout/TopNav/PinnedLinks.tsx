import { Pin } from "lucide-react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { NavItem } from "../../buildNav";

export function PinnedLinks({ items, pathname, onNavigate }: {
  items: NavItem[];
  pathname: string;
  onNavigate?: () => void;
}) {
  if (items.length === 0) return null;
  return (
    <ul aria-label={t("navigation.pins")} className="flex flex-wrap justify-center gap-2 px-2 py-1">
      {items.map((item) => (
        <li key={item.path}>
          <Link to={item.path} onClick={onNavigate}
            aria-current={pathname === item.path ? "page" : undefined}
            className="flex items-center gap-1.5 rounded-md border border-border px-2 py-1 text-sm hover:bg-muted">
            <Pin className="size-3.5" aria-hidden="true" />
            {t(item.labelKey)}
          </Link>
        </li>
      ))}
    </ul>
  );
}
