import { useNavigate } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ANALYSIS_POLL_MS } from "../../hooks/usePostings";
import { usePosting } from "../../hooks/usePosting";
import { DeleteSection } from "./DeleteSection";
import { PostingBody } from "./PostingBody";
import { PostingHeader } from "./PostingHeader";

const LIST_PATH = "/carriere/offres";

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
    if (query.error instanceof ApiError && query.error.status === 404) {
      return (
        <EmptyState
          title={t("gap.posting.notFoundTitle")}
          description={t("gap.errors.notFound")}
          action={{
            label: t("gap.posting.notFoundAction"),
            onClick: () => void navigate(LIST_PATH),
          }}
        />
      );
    }
    if (query.isError) {
      return (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      );
    }
    return <LoadingState label={t("gap.posting.loading")} />;
  }

  const title = posting.title ?? posting.analysis?.title ?? t("gap.posting.untitled");
  return (
    <div className="flex flex-col gap-6">
      <PostingHeader title={title} company={posting.company} />
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
