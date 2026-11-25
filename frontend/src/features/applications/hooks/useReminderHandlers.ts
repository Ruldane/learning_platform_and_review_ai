import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { copyToClipboard } from "../clipboard";
import type { ReminderView } from "../types";
import { useReminderActions } from "./useReminders";

/**
 * The `ReminderCard` actions of a page: Copy (device clipboard), Fait (or
 * « Classer en Sans réponse » for `close_21`), Reporter, Ignorer. A running action blocks one
 * other; `message` announces the handled reminder; `onHandled` hands control back to the page.
 */
export function useReminderHandlers(reminders: ReminderView[], onHandled?: () => void) {
  const actions = useReminderActions();
  const [message, setMessage] = useState("");

  async function run(id: string, choice: "done" | "postpone" | "ignore") {
    const reminder = reminders.find((item) => item.id === id);
    if (!reminder || actions.pending) return;
    const closing = choice === "done" && reminder.kind === "close_21";
    setMessage("");
    const done = await actions.act(reminder, closing ? "close" : choice);
    if (!done) return;
    setMessage(
      t(closing ? "applications.remindersPage.closed" : "applications.remindersPage.handled"),
    );
    onHandled?.();
  }

  return {
    cardProps: {
      onCopy: copyToClipboard,
      onDone: (id: string) => void run(id, "done"),
      onPostpone: (id: string) => void run(id, "postpone"),
      onIgnore: (id: string) => void run(id, "ignore"),
      pending: actions.pending,
    },
    message,
    error: actions.error,
  };
}
