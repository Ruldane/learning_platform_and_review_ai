import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

/** Back to the list, the posting title and its company. */
export function PostingHeader({ title, company }: { title: string; company: string | null }) {
  return (
    <header className="flex flex-col gap-1">
      <Link to="/career/postings" className="text-sm underline">
        {t("gap.posting.back")}
      </Link>
      <h1 className="text-2xl font-semibold">{title}</h1>
      {company ? <p className="text-muted-foreground">{company}</p> : null}
    </header>
  );
}
