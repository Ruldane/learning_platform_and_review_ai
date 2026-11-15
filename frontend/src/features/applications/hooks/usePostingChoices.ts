import { useQuery } from "@tanstack/react-query";
import { fetchPostings } from "../api";
import { applicationsKeys } from "../queryKeys";
import type { PostingSummaryOut } from "../types";

/** Une offre à choisir : son identifiant et son intitulé lisible. */
export interface PostingChoice {
  id: string;
  label: string;
}

// Une fonction stable : TanStack Query ne refait pas la conversion à chaque rendu.
const toChoices = (rows: PostingSummaryOut[]): PostingChoice[] =>
  rows
    .filter((row) => row.status === "ready")
    .map((row) => ({
      id: row.id,
      label: [row.company, row.title].filter(Boolean).join(", ") || row.id,
    }));

/** `GET /postings` : les offres analysées, à choisir pour un entretien sans fiche. */
export function usePostingChoices() {
  return useQuery({
    queryKey: applicationsKeys.postings,
    queryFn: ({ signal }) => fetchPostings(signal),
    select: toChoices,
  });
}
