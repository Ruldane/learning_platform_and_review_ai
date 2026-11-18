import { useQuery } from "@tanstack/react-query";
import { cvPdfUrl, fetchPostingCvs } from "../api";
import type { PostingCv } from "../components/PostingCvList";
import { gapKeys } from "../queryKeys";

/** Les CV prêts générés pour cette offre, avec leur lien de téléchargement. */
export function usePostingCvs(postingId: string): PostingCv[] | undefined {
  const query = useQuery({
    queryKey: gapKeys.cvs(postingId),
    queryFn: ({ signal }) => fetchPostingCvs(postingId, signal),
  });
  return query.data
    ?.filter((version) => version.status === "ready")
    .map((version) => ({
      id: version.id,
      number: version.number,
      createdAt: version.created_at,
      pdfUrl: cvPdfUrl(version.id),
    }));
}
