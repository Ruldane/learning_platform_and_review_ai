import { useQuery } from "@tanstack/react-query";
import { fetchProjects } from "../api";
import { projectKeys } from "../queryKeys";
import { toCardView } from "../toView";

/** The Portfolio: `GET /projects`, re-read each time the page opens (a status may have changed). */
export function useProjects() {
  return useQuery({
    queryKey: projectKeys.list,
    queryFn: ({ signal }) => fetchProjects(signal),
    select: (projects) => projects.map(toCardView),
    staleTime: 0,
  });
}
