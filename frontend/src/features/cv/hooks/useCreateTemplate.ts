import { useMutation, useQueryClient } from "@tanstack/react-query";
import { activateTemplate, createTemplate, type TemplateSource } from "../api";
import { cvErrorMessage, errorCode } from "../errors";
import { cvKeys } from "../queryKeys";

/** `POST /cv/templates` : renvoie l'identifiant du modèle créé à `onCreated`. */
export function useCreateTemplate(onCreated: (templateId: string) => void) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (source: TemplateSource) => createTemplate(source),
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
    error: mutation.isError ? cvErrorMessage(mutation.error) : null,
    /** Un 409 `vision_unavailable` renvoie vers les réglages. */
    visionUnavailable: mutation.isError && errorCode(mutation.error) === "vision_unavailable",
  };
}

/** `POST /cv/templates/{id}/activate` : le modèle devient le seul actif. */
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
