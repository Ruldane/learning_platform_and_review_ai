import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { useLaunchSource } from "@/shared/session-ui";
import { activateTemplate, createTemplate, type TemplateSource } from "../api";
import { cvErrorMessage, errorCode } from "../errors";
import { cvKeys } from "../queryKeys";

/**
 * The text of a creation refusal. `capture_in_progress` keeps the back end message (a capture of
 * template is running): the profile text talks about reading documents, which is wrong here.
 */
const createMessage = (error: unknown): string =>
  errorCode(error) === "capture_in_progress" ? errorMessage(error) : cvErrorMessage(error);

/** `POST /cv/templates`: passes the id of the created template to `onCreated`. */
export function useCreateTemplate(onCreated: (templateId: string) => void) {
  const client = useQueryClient();
  const provider = useLaunchSource();
  const mutation = useMutation({
    mutationFn: (source: TemplateSource) => createTemplate(source, provider.source),
    onSuccess: (created) => {
      void client.invalidateQueries({ queryKey: cvKeys.templates });
      onCreated(created.template_id);
    },
  });
  const { mutate, reset } = mutation;
  return {
    create: (source: TemplateSource) => {
      reset();
      mutate(source);
    },
    pending: mutation.isPending,
    error: mutation.isError ? createMessage(mutation.error) : null,
    launchMenu: provider.menu,
    /** A 409 `vision_unavailable` points to the settings. */
    visionUnavailable: mutation.isError && errorCode(mutation.error) === "vision_unavailable",
  };
}

/** `POST /cv/templates/{id}/activate`: the template becomes the only active one. */
export function useActivateTemplate() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (templateId: string) => activateTemplate(templateId),
    onSuccess: () => client.invalidateQueries({ queryKey: cvKeys.templates }),
  });
  return {
    activate: (templateId: string) => mutation.mutate(templateId),
    pending: mutation.isPending,
    error: mutation.isError ? cvErrorMessage(mutation.error) : null,
  };
}
