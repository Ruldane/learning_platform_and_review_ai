import { useRef } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ReminderCard } from "../../components/ReminderCard";
import { useReminderHandlers } from "../../hooks/useReminderHandlers";
import type { ReminderView } from "../../types";
import { DrawerSection } from "./DrawerSection";

/** This record's pending reminders, with the same buttons as the reminders page. */
export function DrawerReminders({ reminders }: { reminders: ReminderView[] }) {
  const done = useRef<HTMLParagraphElement>(null);
  const handlers = useReminderHandlers(reminders, () => done.current?.focus());
  return (
    <DrawerSection title={t("applications.drawer.remindersTitle")}>
      <p
        ref={done}
        tabIndex={-1}
        role="status"
        className="text-sm text-muted-foreground outline-none"
      >
        {handlers.message}
      </p>
      {handlers.error ? <InlineError message={handlers.error} /> : null}
      {reminders.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("applications.drawer.remindersNone")}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {reminders.map((reminder) => (
            <li key={reminder.id}>
              <ReminderCard reminder={reminder} headingLevel={4} {...handlers.cardProps} />
            </li>
          ))}
        </ul>
      )}
    </DrawerSection>
  );
}
