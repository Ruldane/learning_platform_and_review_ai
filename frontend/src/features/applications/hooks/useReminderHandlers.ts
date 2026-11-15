import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { copyToClipboard } from "../clipboard";
import type { ReminderView } from "../types";
import { useReminderActions } from "./useReminders";

/**
 * Les rappels des `ReminderCard` d'une page : Copier (presse-papiers de l'appareil), Fait (ou
 * « Classer en Sans réponse » pour `close_21`), Reporter, Ignorer. Une action en cours en empêche une
 * autre ; `message` annonce la relance traitée ; `onHandled` rend la main à la page (focus).
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
    },
    message,
    error: actions.error,
  };
}
