import { useQuery } from "@tanstack/react-query";
import { fetchStats } from "../api";
import { applicationsKeys } from "../queryKeys";

/** Les relances arrivent à l'heure près (tâche planifiée) : on relit le compte de temps en temps. */
const REFRESH_MS = 5 * 60 * 1000;

const dueOf = (stats: { due_reminders: number }) => stats.due_reminders;

/**
 * Le nombre de relances dues, pour la pastille de la navigation : la requête des indicateurs, donc
 * partagée avec le tableau. `undefined` tant qu'il n'est pas connu (ou en cas de panne) : pas de pastille.
 */
export function useDueCount(): number | undefined {
  return useQuery({
    queryKey: applicationsKeys.stats,
    queryFn: ({ signal }) => fetchStats(signal),
    select: dueOf,
    refetchInterval: REFRESH_MS,
  }).data;
}
