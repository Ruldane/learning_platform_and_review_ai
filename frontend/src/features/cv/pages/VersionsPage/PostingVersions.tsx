import { useState } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { VersionList } from "../../components/VersionList";
import { toVersionView } from "../../toView";
import type { PostingGroup } from "./groupByPosting";
import { OpenedVersion } from "./OpenedVersion";

const link = "text-sm font-medium underline underline-offset-4";

/** Les versions d'une offre : la liste, et l'aperçu de celle qu'on ouvre. */
export function PostingVersions({ group }: { group: PostingGroup }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const title = group.label ?? t("cv.versionsPage.unknownOffer");
  const reviewId = group.versions[0]?.review_id;
  return (
    <section aria-label={t("cv.versionsPage.group", { title })} className="flex flex-col gap-3">
      <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="text-lg font-medium">{title}</h2>
        {group.label !== null ? (
          <Link to={`/career/postings/${group.postingId}`} className={link}>
            {t("cv.versionsPage.openOffer")}
          </Link>
        ) : null}
        {reviewId ? (
          <Link to={`/career/cv/reviews/${reviewId}`} className={link}>
            {t("cv.versionsPage.openReview")}
          </Link>
        ) : null}
      </header>
      <VersionList versions={group.versions.map(toVersionView)} onOpen={setOpenId} />
      {openId !== null ? (
        <OpenedVersion versionId={openId} onClose={() => setOpenId(null)} />
      ) : null}
    </section>
  );
}
