import { useParams } from "react-router";
import type { SocketFactory } from "@/shared/realtime/socket";
import { PostingView } from "./PostingView";

interface PostingPageProps {
  /** Intervalle de relecture, en ms (réduit par les tests). */
  pollMs?: number;
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * Une offre (`/career/postings/:postingId`). Pendant l'analyse : le fil de la session et une
 * relecture toutes les 3 s, 40 fois. Ensuite : la fiche, les doublons, l'écart avec le profil,
 * « Ajouter au planning » et « Revoir mon CV pour cette offre ». La suppression se confirme dans
 * la page.
 */
export function PostingPage(props: PostingPageProps) {
  const { postingId = "" } = useParams();
  // Une autre offre (ex. un doublon ouvert depuis cette page) repart d'un état vierge.
  return <PostingView key={postingId} postingId={postingId} {...props} />;
}
