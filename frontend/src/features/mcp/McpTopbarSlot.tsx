import { PendingBadge } from "./components/PendingBadge";
import { usePendingCount } from "./hooks/usePendingCount";

/**
 * The feature's `topbar` slot: the « À confirmer (n) » badge, only when there are
 * open requests. Silent while the account is unknown or on failure.
 */
export function McpTopbarSlot() {
  const count = usePendingCount();
  return count ? <PendingBadge count={count} /> : null;
}
