import { useQuery } from "@tanstack/react-query";
import { fetchDebateRounds } from "../api";
import { learningKeys } from "../queryKeys";

const MINUTE_MS = 60_000;

/** Nombre de tours voulu (réglage `debate_rounds`) ; `undefined` tant qu'il n'est pas lu : trois tours. */
export function useDebateRounds(): number | undefined {
  const query = useQuery({
    queryKey: learningKeys.rounds,
    queryFn: ({ signal }) => fetchDebateRounds(signal),
    staleTime: MINUTE_MS,
    retry: false,
  });
  return query.data;
}
