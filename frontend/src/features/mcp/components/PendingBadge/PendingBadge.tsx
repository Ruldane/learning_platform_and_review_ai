import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

/** La pastille « À confirmer (n) » de la barre du haut : un lien vers la page des demandes. */
export function PendingBadge({ count }: { count: number }) {
  return (
    <Link
      to="/reglages/mcp"
      aria-label={t(count === 1 ? "mcp.topbar.label.one" : "mcp.topbar.label.many", { count })}
      className="rounded-lg border border-border bg-background px-2.5 py-1 text-sm font-medium outline-none hover:bg-muted focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring"
    >
      {t("mcp.topbar.pending", { count })}
    </Link>
  );
}
