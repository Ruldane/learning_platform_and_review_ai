import { useQuery } from "@tanstack/react-query";
import { fetchPrograms } from "../api";
import { lessonsKeys } from "../queryKeys";

/** Les programmes (`GET /programs`), du plus récent au plus ancien. */
export function usePrograms() {
  return useQuery({
    queryKey: lessonsKeys.programs,
    queryFn: ({ signal }) => fetchPrograms(signal),
  });
}
