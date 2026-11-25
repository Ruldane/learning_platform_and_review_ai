import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchTemplate, fetchTemplates } from "../api";
import { cvKeys } from "../queryKeys";
import { POLL_MS } from "./useProfile";

/** A template whose capture is running or awaiting review is reloaded regularly. */
export const isOpen = (status: string): boolean => status === "capturing" || status === "review";

/** `GET /cv/templates`; reloaded while a template is being captured or needs validation. */
export function useTemplates(pollMs = POLL_MS) {
  return useQuery({
    queryKey: cvKeys.templates,
    queryFn: ({ signal }) => fetchTemplates(signal),
    refetchInterval: (state) => (state.state.data?.some((t) => isOpen(t.status)) ? pollMs : false),
  });
}

/** `GET /cv/templates/{id}`; reloaded while the capture runs or awaits review. */
export function useTemplate(templateId: string, pollMs = POLL_MS) {
  return useQuery({
    queryKey: cvKeys.template(templateId),
    queryFn: ({ signal }) => fetchTemplate(templateId, signal),
    refetchInterval: (state) =>
      state.state.data && isOpen(state.state.data.status) ? pollMs : false,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
