import { useQuery } from "@tanstack/react-query";
import { fetchDebateRounds } from "../api";
import { learningKeys } from "../queryKeys";

const MINUTE_MS = 60_000;

/** Rounds wanted (`debate_rounds` setting); `undefined` until it is read: three rounds. */
export function useDebateRounds(): number | undefined {
  const query = useQuery({
    queryKey: learningKeys.rounds,
    queryFn: ({ signal }) => fetchDebateRounds(signal),
    staleTime: MINUTE_MS,
    retry: false,
  });
  return query.data;
}
