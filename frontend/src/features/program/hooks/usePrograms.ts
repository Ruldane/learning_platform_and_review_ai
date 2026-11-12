import { useQuery } from "@tanstack/react-query";
import { fetchPrograms } from "../api";
import { programKeys } from "../queryKeys";

/** Les programmes (`GET /programs`), du plus récent au plus ancien : le premier est « le programme ». */
export function usePrograms() {
  return useQuery({
    queryKey: programKeys.list,
    queryFn: ({ signal }) => fetchPrograms(signal),
  });
}
