import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { PostingListItemView } from "../viewTypes";

interface PostingListProps {
  postings: PostingListItemView[];
  /** The address of a posting's page. */
  hrefOf: (postingId: string) => string;
}

function statusText(posting: PostingListItemView): string | null {
  switch (posting.status) {
    case "analyzing":
      return t("gap.postings.analyzing");
    case "rejected":
      return t("gap.postings.rejected");
    case "failed":
      return t("gap.postings.failed");
    default:
      return posting.score === null ? null : t("gap.postings.score", { score: posting.score });
  }
}

/** The added postings: title (link to the posting), company, and score or status. */
export function PostingList({ postings, hrefOf }: PostingListProps) {
  return (
    <ul aria-label={t("gap.postings.listLabel")} className="flex flex-col gap-2">
      {postings.map((posting) => {
        const status = statusText(posting);
        return (
          <li
            key={posting.id}
            className="flex flex-wrap items-baseline justify-between gap-2 rounded-xl border bg-card p-3"
          >
            <div className="flex flex-col">
              <Link
                to={hrefOf(posting.id)}
                className="font-medium text-primary underline underline-offset-2"
              >
                {posting.title ?? t("gap.postings.untitled")}
              </Link>
              {posting.company ? (
                <span className="text-sm text-muted-foreground">{posting.company}</span>
              ) : null}
            </div>
            {status ? (
              <span
                data-status={posting.status}
                role={posting.status === "analyzing" ? "status" : undefined}
                className="text-sm text-muted-foreground"
              >
                {status}
              </span>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
