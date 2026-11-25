import { useQuery } from "@tanstack/react-query";
import { fetchPostings } from "../api";
import { applicationsKeys } from "../queryKeys";
import type { PostingSummaryOut } from "../types";

/** A posting to choose: its identifier and readable title. */
export interface PostingChoice {
  id: string;
  label: string;
}

// A stable function: TanStack Query does not redo the conversion on each render.
const toChoices = (rows: PostingSummaryOut[]): PostingChoice[] =>
  rows
    .filter((row) => row.status === "ready")
    .map((row) => ({
      id: row.id,
      label: [row.company, row.title].filter(Boolean).join(", ") || row.id,
    }));

/** `GET /postings`: analysed postings for a free interview (not read without `enabled`). */
export function usePostingChoices(enabled = true) {
  return useQuery({
    queryKey: applicationsKeys.postings,
    queryFn: ({ signal }) => fetchPostings(signal),
    select: toChoices,
    enabled,
  });
}
