import { useQuery } from "@tanstack/react-query";
import { readReturn, studyReturnKey } from "./api";

export function useStudyReturn() {
  return useQuery({ queryKey: studyReturnKey, queryFn: ({ signal }) => readReturn(signal) });
}

export function useStudyReturnBadge() {
  return useStudyReturn().data?.reminder_due ? 1 : undefined;
}
