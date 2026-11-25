import { useMemo } from "react";
import { Link, useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useLaunchSource } from "@/shared/session-ui";
import { buttonVariants } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { DuplicateNotice } from "../../components/DuplicateNotice";
import { PostingCvList } from "../../components/PostingCvList";
import { PostingAnalysisCard } from "../../components/PostingAnalysisCard";
import { useMarkDistinct } from "../../hooks/useMarkDistinct";
import { usePostingCvs } from "../../hooks/usePostingCvs";
import { toAnalysisView, toDuplicateViews } from "../../toView";
import type { PostingOut } from "../../types";
import { ApplicationBlock } from "./ApplicationBlock";
import { GapSection } from "./GapSection";

interface ReadyBlockProps {
  posting: PostingOut;
  pollMs: number;
  createSocket?: SocketFactory;
}

/**
 * An analyzed posting: its record, the postings that resemble it (re-read with the analysis, G35),
 * the gap with the profile, then the links to the CV review and the listing.
 */
export function ReadyBlock({ posting, pollMs, createSocket }: ReadyBlockProps) {
  const navigate = useNavigate();
  const provider = useLaunchSource();
  const { distinct, error } = useMarkDistinct(posting.id);
  const cvs = usePostingCvs(posting.id);
  const analysis = useMemo(
    () => (posting.analysis ? toAnalysisView(posting.analysis) : null),
    [posting.analysis],
  );
  const duplicates = useMemo(() => toDuplicateViews(posting.duplicates), [posting.duplicates]);
  return (
    <>
      <DuplicateNotice
        duplicates={duplicates}
        onOpen={(postingId) => void navigate(`/career/postings/${postingId}`)}
        onDistinct={distinct}
      />
      {error ? <InlineError message={error} /> : null}
      {analysis ? <PostingAnalysisCard analysis={analysis} showTitle={false} /> : null}
      <GapSection postingId={posting.id} pollMs={pollMs} createSocket={createSocket} />
      <ApplicationBlock postingId={posting.id} />
      {cvs ? <PostingCvList cvs={cvs} /> : null}
      <div className="flex flex-wrap items-end gap-2">
        {provider.menu}
        <Link
          to={`/career/cv/reviews/new/${posting.id}`}
          state={{ runSource: provider.source }}
          className={buttonVariants()}
        >
          {t("gap.posting.reviewCv")}
        </Link>
        {posting.url ? (
          <a
            href={posting.url}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: "outline" })}
          >
            {t("gap.posting.sourceLink")}
          </a>
        ) : null}
      </div>
    </>
  );
}
