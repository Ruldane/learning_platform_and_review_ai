import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { DuplicateNotice } from "../../components/DuplicateNotice";
import { certainDuplicate } from "../../toView";
import type { PostingCreatedOut } from "../../types";

/**
 * The same link or text is already in the list (200 response): the « déjà ajoutée » notice
 * (certain duplicate), then the link to the posting. A restarted analysis is said so.
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
        to={`/career/postings/${posting.id}`}
        className={buttonVariants({ variant: "outline", className: "self-start" })}
      >
        {t("gap.postings.openExisting")}
      </Link>
    </div>
  );
}
