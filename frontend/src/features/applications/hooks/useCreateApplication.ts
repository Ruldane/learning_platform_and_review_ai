import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createApplication } from "../api";
import { applicationsErrorMessage, duplicateAlerts } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { AlertOut, ApplicationIn, CreatedOut } from "../types";

/**
 * `POST /applications`. Un 409 `application_duplicate` ne s'affiche pas comme une erreur : ses
 * fiches proches (`alerts`) alimentent l'alerte de doublon. `create` rend la fiche créée (avec les
 * informations « même entreprise »), ou `null` si elle ne l'est pas.
 */
export function useCreateApplication() {
  const client = useQueryClient();
  const [alerts, setAlerts] = useState<AlertOut[]>([]);
  const mutation = useMutation({
    mutationFn: (body: ApplicationIn) => createApplication(body),
    onSuccess: () => client.invalidateQueries({ queryKey: applicationsKeys.all }),
  });
  const { mutateAsync, reset } = mutation;

  async function create(body: ApplicationIn): Promise<CreatedOut | null> {
    reset();
    setAlerts([]);
    try {
      return await mutateAsync(body);
    } catch (error) {
      setAlerts(duplicateAlerts(error) ?? []);
      return null;
    }
  }

  // Un doublon n'est pas une panne : son alerte (ou, une fois fermée, rien) le dit.
  const failed = mutation.isError && duplicateAlerts(mutation.error) === null;
  return {
    create,
    alerts,
    clearAlerts: () => setAlerts([]),
    pending: mutation.isPending,
    error: failed ? applicationsErrorMessage(mutation.error) : null,
  };
}
