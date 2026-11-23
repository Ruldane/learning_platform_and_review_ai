import { useQuery } from "@tanstack/react-query";
import { fetchOverview } from "../api";

export function useLabOverview() {
  return useQuery({
    queryKey: ["lab", "overview"],
    queryFn: ({ signal }) => fetchOverview(signal),
  });
}
