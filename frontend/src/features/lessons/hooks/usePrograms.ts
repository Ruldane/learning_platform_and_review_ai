import { useQuery } from "@tanstack/react-query";
import { fetchPrograms } from "../api";
import { lessonsKeys } from "../queryKeys";

/** The programs (`GET /programs`), newest first. */
export function usePrograms() {
  return useQuery({
    queryKey: lessonsKeys.programs,
    queryFn: ({ signal }) => fetchPrograms(signal),
  });
}
