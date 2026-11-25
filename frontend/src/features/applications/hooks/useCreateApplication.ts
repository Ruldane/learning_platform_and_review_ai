import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createApplication } from "../api";
import { applicationsErrorMessage, duplicateAlerts } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { AlertOut, ApplicationIn, CreatedOut } from "../types";

/**
 * `POST /applications`. A 409 `application_duplicate` is not shown as an error: its
 * near-matching records (`alerts`) feed the duplicate alert. `create` returns the created record
 * (with the
 * « même entreprise » information), or `null` if it is not.
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

  // A duplicate is not a failure: its alert (or, once closed, nothing) says so.
  const failed = mutation.isError && duplicateAlerts(mutation.error) === null;
  return {
    create,
    alerts,
    clearAlerts: () => setAlerts([]),
    pending: mutation.isPending,
    error: failed ? applicationsErrorMessage(mutation.error) : null,
  };
}
