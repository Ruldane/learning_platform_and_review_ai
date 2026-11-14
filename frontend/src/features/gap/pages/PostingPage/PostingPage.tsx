import { Link, useNavigate, useParams } from "react-router";
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

interface PostingPageProps {
  /** Intervalle de relecture, en ms (réduit par les tests). */
  pollMs?: number;
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

const LIST_PATH = "/carriere/offres";

/**
 * Une offre (`/carriere/offres/:postingId`). Pendant l'analyse : le fil de la session et une
 * relecture toutes les 3 s, 40 fois. Ensuite : la fiche, les doublons, l'écart avec le profil,
 * « Ajouter au planning » et « Revoir mon CV pour cette offre ». La suppression se confirme dans
 * la page.
 */
export function PostingPage({ pollMs = ANALYSIS_POLL_MS, createSocket }: PostingPageProps) {
  const { postingId = "" } = useParams();
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
      <header className="flex flex-col gap-1">
        <Link to={LIST_PATH} className="text-sm underline">
          {t("gap.posting.back")}
        </Link>
        <h1 className="text-2xl font-semibold">{title}</h1>
        {posting.company ? <p className="text-muted-foreground">{posting.company}</p> : null}
      </header>
      <PostingBody
        posting={posting}
        budget={budget}
        pollMs={pollMs}
        onRetry={() => void query.refetch()}
        createSocket={createSocket}
      />
      <DeleteSection postingId={posting.id} onDeleted={() => void navigate(LIST_PATH)} />
    </div>
  );
}
