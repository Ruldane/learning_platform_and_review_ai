import { useQuery } from "@tanstack/react-query";
import { fetchRunningLearnings } from "../api";
import { memoryKeys } from "../queryKeys";

/**
 * Sessions de l'Archiviste encore en cours (`GET /sessions` filtré), lues une fois au montage de
 * l'écran Documents pour reprendre le suivi après un rechargement. Aucune interrogation
 * périodique : le flux de chaque session prend le relais.
 */
export function useRunningLearnings() {
  return useQuery({
    queryKey: memoryKeys.runningLearnings,
    queryFn: ({ signal }) => fetchRunningLearnings(signal),
    refetchOnWindowFocus: false,
  });
}
