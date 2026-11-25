import { t } from "@/shared/i18n/t";
import type { PostingRefView } from "../viewTypes";
import { SmartLink } from "./SmartLink";

/** The offers that require the skill; empty until the gap analysis exists (phase 6). */
export function PostingList({ postings }: { postings: PostingRefView[] }) {
  if (postings.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("skills.drawer.postingsEmpty")}</p>;
  }
  return (
    <ul aria-label={t("skills.drawer.postings")} className="flex flex-col gap-1 text-sm">
      {postings.map((posting) => (
        <li key={posting.id}>
          {posting.url ? <SmartLink url={posting.url}>{posting.title}</SmartLink> : posting.title}
        </li>
      ))}
    </ul>
  );
}
