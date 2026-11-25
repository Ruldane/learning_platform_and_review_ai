import { useQuery } from "@tanstack/react-query";
import { fetchDocuments } from "../api";
import { memoryKeys } from "../queryKeys";
import { toDocumentRow } from "../toView";
import type { DocumentOut } from "../types";

const POLL_MS = 2000;

/** A document is waiting or being indexed: the screen polls the server every 2 s. */
export function hasDocumentInFlight(documents: Pick<DocumentOut, "status">[] | undefined): boolean {
  return (documents ?? []).some((d) => d.status === "queued" || d.status === "processing");
}

/** Imported documents (`GET /documents`), re-read every 2 s while one is queued or in progress. */
export function useDocuments() {
  return useQuery({
    queryKey: memoryKeys.documents,
    queryFn: ({ signal }) => fetchDocuments(signal),
    refetchInterval: (q) => (hasDocumentInFlight(q.state.data) ? POLL_MS : false),
    select: (data: DocumentOut[]) => data.map(toDocumentRow),
  });
}
