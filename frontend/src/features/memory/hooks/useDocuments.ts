import { useQuery } from "@tanstack/react-query";
import { fetchDocuments } from "../api";
import { memoryKeys } from "../queryKeys";
import { toDocumentRow } from "../toView";
import type { DocumentOut } from "../types";

const POLL_MS = 2000;

/** Un document attend ou est en cours d'indexation : l'écran interroge le serveur toutes les 2 s. */
export function hasDocumentInFlight(documents: Pick<DocumentOut, "status">[] | undefined): boolean {
  return (documents ?? []).some((d) => d.status === "queued" || d.status === "processing");
}

/** Documents importés (`GET /documents`), relus toutes les 2 s tant que l'un est en file ou en cours. */
export function useDocuments() {
  return useQuery({
    queryKey: memoryKeys.documents,
    queryFn: ({ signal }) => fetchDocuments(signal),
    refetchInterval: (q) => (hasDocumentInFlight(q.state.data) ? POLL_MS : false),
    select: (data: DocumentOut[]) => data.map(toDocumentRow),
  });
}
