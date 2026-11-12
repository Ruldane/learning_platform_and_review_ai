import { useQuery } from "@tanstack/react-query";
import { fetchProgram } from "../api";
import { programKeys } from "../queryKeys";

/** Un programme (`GET /programs/{id}`) : semaines, modules, tâches, avancement et différence de version. */
export function useProgram(programId: string) {
  return useQuery({
    queryKey: programKeys.detail(programId),
    queryFn: ({ signal }) => fetchProgram(programId, signal),
  });
}
