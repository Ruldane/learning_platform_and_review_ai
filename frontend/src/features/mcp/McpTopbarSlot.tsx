import { PendingBadge } from "./components/PendingBadge";
import { usePendingCount } from "./hooks/usePendingCount";

/**
 * Emplacement `topbar` de la feature : la pastille « À confirmer (n) », seulement quand il y a des
 * demandes ouvertes. Muette tant que le compte est inconnu ou en cas de panne.
 */
export function McpTopbarSlot() {
  const count = usePendingCount();
  return count ? <PendingBadge count={count} /> : null;
}
