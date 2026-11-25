import { useQuery } from "@tanstack/react-query";
import { fetchPrograms } from "../api";
import { programKeys } from "../queryKeys";

/** The programs (`GET /programs`), newest first: the first one is « le programme ». */
export function usePrograms() {
  return useQuery({
    queryKey: programKeys.list,
    queryFn: ({ signal }) => fetchPrograms(signal),
  });
}
