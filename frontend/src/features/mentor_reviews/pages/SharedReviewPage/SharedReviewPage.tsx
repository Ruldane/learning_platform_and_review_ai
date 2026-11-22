import { useLocation } from "react-router";
import { SharedInvitation } from "../SharedInvitation";

export function SharedReviewPage() {
  const token = useLocation().hash.slice(1);
  return <SharedInvitation key={token} token={token} />;
}
