import { useQuery } from "@tanstack/react-query";
import { fetchDocuments, fetchPostingTitles, fetchVersion, fetchVersions } from "../api";
import { cvKeys } from "../queryKeys";

/** `GET /cv/versions`: all CV versions. */
export function useVersions() {
  return useQuery({ queryKey: cvKeys.versions, queryFn: ({ signal }) => fetchVersions(signal) });
}

/** `GET /cv/versions/{id}`; read only while a version is open. */
export function useVersion(versionId: string | null) {
  return useQuery({
    queryKey: cvKeys.version(versionId ?? ""),
    queryFn: ({ signal }) => fetchVersion(versionId ?? "", signal),
    enabled: versionId !== null,
  });
}

/** `GET /postings`: names for the versions' postings. A failure does not block the versions. */
export function usePostingTitles() {
  return useQuery({
    queryKey: cvKeys.postings,
    queryFn: ({ signal }) => fetchPostingTitles(signal),
  });
}

/** `GET /documents`: the PDFs already imported, to make a template from. */
export function useDocuments() {
  return useQuery({
    queryKey: cvKeys.documents,
    queryFn: ({ signal }) => fetchDocuments(signal),
  });
}
