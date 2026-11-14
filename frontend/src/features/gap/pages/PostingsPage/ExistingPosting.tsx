import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { DuplicateNotice } from "../../components/DuplicateNotice";
import { certainDuplicate } from "../../toView";
import type { PostingCreatedOut } from "../../types";

/**
 * Le même lien ou le même texte est déjà dans la liste (réponse 200) : l'avis « déjà ajoutée »
 * (doublon certain) puis le lien vers l'offre. Une analyse relancée est dite.
 */
export function ExistingPosting({ result }: { result: PostingCreatedOut }) {
  const { posting } = result;
  return (
    <div role="status" className="flex flex-col gap-2">
      <DuplicateNotice
        duplicates={[certainDuplicate(posting)]}
        onOpen={() => undefined}
        onDistinct={() => undefined}
      />
      {result.session_id ? (
        <p className="text-sm text-muted-foreground">{t("gap.postings.relaunched")}</p>
      ) : null}
      <Link
        to={`/carriere/offres/${posting.id}`}
        className={buttonVariants({ variant: "outline", className: "self-start" })}
      >
        {t("gap.postings.openExisting")}
      </Link>
    </div>
  );
}
