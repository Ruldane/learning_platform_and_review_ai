import { shortDay } from "@/shared/lib/format";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ReminderItemView } from "../viewTypes";

interface RemindersCardProps {
  /** All reminders due (`items` only shows the first ones). */
  due: number;
  items: ReminderItemView[];
  /** Opens the application record of the reminder. */
  onOpen: (applicationId: string) => void;
  /** The reminders source was down this morning: neither zero nor a list, an honest sentence. */
  unavailable?: boolean;
}

/** Reminders due: company, role and deadline, each leading to its record. */
export function RemindersCard({ due, items, onOpen, unavailable = false }: RemindersCardProps) {
  const hidden = items.length === 0 ? 0 : due - items.length;
  return (
    <section
      aria-labelledby="home-reminders"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h2 id="home-reminders" className="text-lg font-medium">
        {t("home.reminders.title")}
      </h2>
      {unavailable ? (
        <p className="text-muted-foreground">{t("home.unavailable")}</p>
      ) : items.length === 0 ? (
        <p className={due > 0 ? undefined : "text-muted-foreground"}>
          {due === 0
            ? t("home.reminders.none")
            : due === 1
              ? t("home.reminders.due.one")
              : t("home.reminders.due.many", { count: due })}
        </p>
      ) : (
        <ul aria-label={t("home.reminders.listLabel")} className="flex flex-col gap-2 text-sm">
          {items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-baseline justify-between gap-2">
              <Button
                variant="link"
                className="h-auto p-0 whitespace-normal"
                onClick={() => onOpen(item.applicationId)}
              >
                {t("home.reminders.item", { company: item.company, title: item.title })}
              </Button>
              <span className="text-muted-foreground tabular-nums">
                {t("home.reminders.dueOn", { date: shortDay(item.dueOn) })}
              </span>
            </li>
          ))}
        </ul>
      )}
      {hidden > 0 ? (
        <p className="text-sm text-muted-foreground">
          {hidden === 1
            ? t("home.reminders.more.one")
            : t("home.reminders.more.many", { count: hidden })}
        </p>
      ) : null}
    </section>
  );
}
