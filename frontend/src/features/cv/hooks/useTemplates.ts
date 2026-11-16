import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchTemplate, fetchTemplates } from "../api";
import { cvKeys } from "../queryKeys";
import { POLL_MS } from "./useProfile";

/** Un modèle dont la capture tourne ou attend un avis est relu régulièrement. */
export const isOpen = (status: string): boolean => status === "capturing" || status === "review";

/** `GET /cv/templates` ; relu tant qu'un modèle est en capture ou à valider. */
export function useTemplates(pollMs = POLL_MS) {
  return useQuery({
    queryKey: cvKeys.templates,
    queryFn: ({ signal }) => fetchTemplates(signal),
    refetchInterval: (state) => (state.state.data?.some((t) => isOpen(t.status)) ? pollMs : false),
  });
}

/** `GET /cv/templates/{id}` ; relu tant que la capture tourne ou attend un avis. */
export function useTemplate(templateId: string, pollMs = POLL_MS) {
  return useQuery({
    queryKey: cvKeys.template(templateId),
    queryFn: ({ signal }) => fetchTemplate(templateId, signal),
    refetchInterval: (state) =>
      state.state.data && isOpen(state.state.data.status) ? pollMs : false,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
