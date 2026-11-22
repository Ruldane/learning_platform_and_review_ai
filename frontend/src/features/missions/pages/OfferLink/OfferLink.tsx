import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

export function OfferLink({ id, title }: { id: string; title: string | null }) {
  return (
    <li>
      <Link className="underline" to={`?offre=${encodeURIComponent(id)}`}>
        {title ?? t("missions.untitled")}
      </Link>
    </li>
  );
}
