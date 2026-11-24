import { Link, useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ANALYSIS_POLL_MS } from "../../hooks/usePostings";
import { usePosting } from "../../hooks/usePosting";
import { DeleteSection } from "./DeleteSection";
import { PostingBody } from "./PostingBody";
import { PostingHeader } from "./PostingHeader";
import { PostingUnavailable } from "./PostingUnavailable";

const LIST_PATH = "/career/postings";

interface PostingViewProps {
  postingId: string;
  /** Intervalle de relecture, en ms (réduit par les tests). */
  pollMs?: number;
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

/** La page d'une offre, montée sous `key={postingId}` : chaque offre repart d'un état vierge. */
export function PostingView({
  postingId,
  pollMs = ANALYSIS_POLL_MS,
  createSocket,
}: PostingViewProps) {
  const navigate = useNavigate();
  const { query, budget } = usePosting(postingId, pollMs);
  const posting = query.data;

  if (posting === undefined) {
    return (
      <PostingUnavailable
        error={query.error}
        retry={() => void query.refetch()}
        onList={() => void navigate(LIST_PATH)}
      />
    );
  }

  const title = posting.title ?? posting.analysis?.title ?? t("gap.posting.untitled");
  return (
    <div className="flex flex-col gap-6">
      <PostingHeader title={title} company={posting.company} />
      {posting.analysis ? (
        <Link
          className="self-start underline"
          to={`/carriere/missions?offre=${encodeURIComponent(posting.id)}`}
        >
          {t("missions.openFromOffer")}
        </Link>
      ) : null}
      <PostingBody
        posting={posting}
        budget={budget}
        pollMs={pollMs}
        onRetry={() => void query.refetch()}
        createSocket={createSocket}
      />
      <DeleteSection
        postingId={posting.id}
        hasReview={posting.has_review}
        onDeleted={() => void navigate(LIST_PATH)}
      />
    </div>
  );
}
