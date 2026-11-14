import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

/** Le retour à la liste, le titre de l'offre et son entreprise. */
export function PostingHeader({ title, company }: { title: string; company: string | null }) {
  return (
    <header className="flex flex-col gap-1">
      <Link to="/carriere/offres" className="text-sm underline">
        {t("gap.posting.back")}
      </Link>
      <h1 className="text-2xl font-semibold">{title}</h1>
      {company ? <p className="text-muted-foreground">{company}</p> : null}
    </header>
  );
}
