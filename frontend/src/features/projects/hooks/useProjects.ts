import { useQuery } from "@tanstack/react-query";
import { fetchProjects } from "../api";
import { projectKeys } from "../queryKeys";
import { toCardView } from "../toView";

/** Le Portfolio : `GET /projects`, relu à chaque ouverture de la page (un statut a pu changer). */
export function useProjects() {
  return useQuery({
    queryKey: projectKeys.list,
    queryFn: ({ signal }) => fetchProjects(signal),
    select: (projects) => projects.map(toCardView),
    staleTime: 0,
  });
}
