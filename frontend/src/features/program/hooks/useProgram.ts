import { useQuery } from "@tanstack/react-query";
import { fetchProgram } from "../api";
import { programKeys } from "../queryKeys";

/** A program (`GET /programs/{id}`): weeks, modules, tasks, progress and version diff. */
export function useProgram(programId: string) {
  return useQuery({
    queryKey: programKeys.detail(programId),
    queryFn: ({ signal }) => fetchProgram(programId, signal),
  });
}
