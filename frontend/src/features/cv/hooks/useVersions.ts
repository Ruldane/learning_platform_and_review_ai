import { useQuery } from "@tanstack/react-query";
import { fetchDocuments, fetchPostingTitles, fetchVersion, fetchVersions } from "../api";
import { cvKeys } from "../queryKeys";

/** `GET /cv/versions` : toutes les versions de CV. */
export function useVersions() {
  return useQuery({ queryKey: cvKeys.versions, queryFn: ({ signal }) => fetchVersions(signal) });
}

/** `GET /cv/versions/{id}` ; lue seulement quand une version est ouverte. */
export function useVersion(versionId: string | null) {
  return useQuery({
    queryKey: cvKeys.version(versionId ?? ""),
    queryFn: ({ signal }) => fetchVersion(versionId ?? "", signal),
    enabled: versionId !== null,
  });
}

/** `GET /postings` : de quoi nommer les offres des versions. Une panne n'empêche pas d'afficher les versions. */
export function usePostingTitles() {
  return useQuery({
    queryKey: cvKeys.postings,
    queryFn: ({ signal }) => fetchPostingTitles(signal),
  });
}

/** `GET /documents` : les PDF déjà importés, pour en refaire un modèle. */
export function useDocuments() {
  return useQuery({
    queryKey: cvKeys.documents,
    queryFn: ({ signal }) => fetchDocuments(signal),
  });
}
