import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchReminders, patchReminder, postEvent, type ReminderAction } from "../api";
import { applicationsErrorMessage } from "../errors";
import { applicationsKeys } from "../queryKeys";
import { toReminderView } from "../toView";
import type { ReminderOut, ReminderView } from "../types";

const toViews = (rows: ReminderOut[]) => rows.map(toReminderView);

/** `GET /reminders?due=true`: reminders to handle, oldest due date first. */
export function useReminders() {
  return useQuery({
    queryKey: applicationsKeys.reminders,
    queryFn: ({ signal }) => fetchReminders(true, signal),
    select: toViews,
  });
}

type Choice = ReminderAction | "close";

/** Already handled elsewhere (or gone with the record): the wanted result is reached. */
const alreadyClosed = (error: unknown) =>
  error instanceof ApiError &&
  (error.code === "reminder_closed" || error.code === "reminder_not_found");

/**
 * Fait, Reporter by 3 days, Ignorer, and « Classer en Sans réponse » (`close_21`): the record moves
 * to `no_answer` first, then the reminder is marked done (if the status change already
 * closed it, that is just as good). Lists, the navigation count and the records are re-read.
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
    /** Resolves to `true` when the action is done; `false` on a refusal (readable in `error`). */
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
