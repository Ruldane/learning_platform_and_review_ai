import { useMemo } from "react";
import { Link, useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { buttonVariants } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { DuplicateNotice } from "../../components/DuplicateNotice";
import { PostingAnalysisCard } from "../../components/PostingAnalysisCard";
import { useMarkDistinct } from "../../hooks/useMarkDistinct";
import { toAnalysisView, toDuplicateViews } from "../../toView";
import type { PostingOut } from "../../types";
import { GapSection } from "./GapSection";

interface ReadyBlockProps {
  posting: PostingOut;
  pollMs: number;
  createSocket?: SocketFactory;
}

/**
 * Une offre analysée : sa fiche, les offres qui lui ressemblent (relues avec l'analyse, G35),
 * l'écart avec le profil, puis les liens vers la revue du CV et l'annonce.
 */
export function ReadyBlock({ posting, pollMs, createSocket }: ReadyBlockProps) {
  const navigate = useNavigate();
  const { distinct, error } = useMarkDistinct(posting.id);
  const analysis = useMemo(
    () => (posting.analysis ? toAnalysisView(posting.analysis) : null),
    [posting.analysis],
  );
  const duplicates = useMemo(() => toDuplicateViews(posting.duplicates), [posting.duplicates]);
  return (
    <>
      <DuplicateNotice
        duplicates={duplicates}
        onOpen={(postingId) => void navigate(`/carriere/offres/${postingId}`)}
        onDistinct={distinct}
      />
      {error ? <InlineError message={error} /> : null}
      {analysis ? <PostingAnalysisCard analysis={analysis} /> : null}
      <GapSection postingId={posting.id} pollMs={pollMs} createSocket={createSocket} />
      <div className="flex flex-wrap gap-2">
        <Link to={`/carriere/cv/revue/nouvelle/${posting.id}`} className={buttonVariants()}>
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
