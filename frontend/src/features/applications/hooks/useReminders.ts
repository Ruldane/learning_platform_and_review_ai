import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchReminders, patchReminder, postEvent, type ReminderAction } from "../api";
import { applicationsErrorMessage } from "../errors";
import { applicationsKeys } from "../queryKeys";
import { toReminderView } from "../toView";
import type { ReminderOut, ReminderView } from "../types";

const toViews = (rows: ReminderOut[]) => rows.map(toReminderView);

/** `GET /reminders?due=true` : les relances à traiter, l'échéance la plus ancienne d'abord. */
export function useReminders() {
  return useQuery({
    queryKey: applicationsKeys.reminders,
    queryFn: ({ signal }) => fetchReminders(true, signal),
    select: toViews,
  });
}

type Choice = ReminderAction | "close";

/** Déjà traitée ailleurs (ou disparue avec la fiche) : le résultat voulu est atteint. */
const alreadyClosed = (error: unknown) =>
  error instanceof ApiError &&
  (error.code === "reminder_closed" || error.code === "reminder_not_found");

/**
 * Fait, Reporter de 3 jours, Ignorer, et « Classer en Sans réponse » (`close_21`) : la fiche passe
 * à `no_answer` d'abord, puis la relance est marquée faite (si le changement de statut l'a déjà
 * refermée, c'est tout aussi bien). Les listes, le compte de la navigation et les fiches sont relus.
 */
export function useReminderActions() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: async ({ reminder, choice }: { reminder: ReminderView; choice: Choice }) => {
      if (choice !== "close") {
        await patchReminder(reminder.id, choice);
        return;
      }
      await postEvent(reminder.applicationId, { kind: "status", status: "no_answer" });
      await patchReminder(reminder.id, "done").catch((error: unknown) => {
        if (!alreadyClosed(error)) throw error;
      });
    },
    onSettled: () => client.invalidateQueries({ queryKey: applicationsKeys.all }),
  });
  const { mutateAsync, reset } = mutation;
  return {
    /** Résout à `true` quand l'action est faite ; `false` sur un refus (lisible dans `error`). */
    act: (reminder: ReminderView, choice: Choice): Promise<boolean> => {
      reset();
      return mutateAsync({ reminder, choice }).then(
        () => true,
        () => false,
      );
    },
    pending: mutation.isPending,
    error: mutation.isError ? applicationsErrorMessage(mutation.error) : null,
  };
}
