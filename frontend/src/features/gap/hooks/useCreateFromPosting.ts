import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { createApplicationFromPosting } from "../api";
import { gapKeys } from "../queryKeys";
import type { ApplicationAlertOut } from "../types";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

function detailsOf(error: unknown): Record<string, unknown> {
  return error instanceof ApiError && isRecord(error.details) ? error.details : {};
}

interface Created {
  id: string;
  /** Les informations « même entreprise » à montrer sur la fiche ouverte. */
  info: ApplicationAlertOut[];
}

/**
 * Crée la candidature d'une offre. `create` rend la fiche à ouvrir : celle qui vient d'être créée
 * (avec ses informations « même entreprise »), ou celle que l'offre a déjà (409 `application_exists`).
 * Des fiches qui ressemblent (409 `application_duplicate`) rendent `null` et remplissent `conflict` :
 * January confirme « autre poste » en rappelant `create` avec leurs identifiants. Toute autre
 * erreur est dans `error`.
 */
export function useCreateFromPosting(postingId: string) {
  const client = useQueryClient();
  const [conflict, setConflict] = useState<ApplicationAlertOut[]>([]);
  const mutation = useMutation({
    mutationFn: (distinctFrom: string[]) => createApplicationFromPosting(postingId, distinctFrom),
    onSuccess: () => client.invalidateQueries({ queryKey: gapKeys.applicationCheck(postingId) }),
  });
  const { mutateAsync, reset } = mutation;

  async function create(distinctFrom: string[] = []): Promise<Created | null> {
    reset();
    setConflict([]);
    try {
      const created = await mutateAsync(distinctFrom);
      return { id: created.application.id, info: created.info };
    } catch (error) {
      const details = detailsOf(error);
      const code = error instanceof ApiError ? error.code : null;
      if (code === "application_exists" && typeof details.application_id === "string") {
        return { id: details.application_id, info: [] };
      }
      if (code === "application_duplicate" && Array.isArray(details.alerts)) {
        setConflict(details.alerts as ApplicationAlertOut[]);
      }
      return null;
    }
  }

  return {
    create,
    conflict,
    pending: mutation.isPending,
    error: mutation.isError && conflict.length === 0 ? errorMessage(mutation.error) : null,
  };
}
