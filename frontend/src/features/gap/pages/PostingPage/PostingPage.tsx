import { useParams } from "react-router";
import type { SocketFactory } from "@/shared/realtime/socket";
import { PostingView } from "./PostingView";

interface PostingPageProps {
  /** Re-read interval, in ms (shortened by tests). */
  pollMs?: number;
  /** Only used by tests (fake WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * A posting (`/career/postings/:postingId`). During the analysis: the session feed and a
 * re-read every 3 s, 40 times. Then: the record, duplicates, gap with the profile,
 * « Ajouter au planning » and « Revoir mon CV pour cette offre ». Deletion is confirmed in
 * the page.
 */
export function PostingPage(props: PostingPageProps) {
  const { postingId = "" } = useParams();
  // Another posting (e.g. a duplicate opened from this page) starts from a blank state.
  return <PostingView key={postingId} postingId={postingId} {...props} />;
}
