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
  /** The « même entreprise » notes to show on the opened card. */
  info: ApplicationAlertOut[];
}

/**
 * Creates a posting's application. `create` returns the card to open: the one just created
 * (with its « même entreprise » notes), or the posting's own (409 `application_exists`).
 * Cards that resemble it (409 `application_duplicate`) return `null` and fill `conflict`:
 * January confirms « autre poste » by calling `create` again with their ids. Any other
 * error goes to `error`.
 */
export function useCreateFromPosting(postingId: string) {
  const client = useQueryClient();
  const [conflict, setConflict] = useState<ApplicationAlertOut[]>([]);
  const mutation = useMutation({
    mutationFn: (distinctFrom: string[]) => createApplicationFromPosting(postingId, distinctFrom),
    onSuccess: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: gapKeys.applicationCheck(postingId) }),
        // Tracking, indicators and the follow-up badge see the new card (the prefix of
        // the `applications` feature, which `gap` does not import).
        client.invalidateQueries({ queryKey: ["applications"] }),
      ]),
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
