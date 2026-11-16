import { shortDay } from "@/shared/lib/format";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ReminderItemView } from "../viewTypes";

interface RemindersCardProps {
  /** Toutes les relances dues (`items` n'en montre que les premières). */
  due: number;
  items: ReminderItemView[];
  /** Ouvre la fiche de candidature de la relance. */
  onOpen: (applicationId: string) => void;
}

/** Les relances dues : entreprise, poste et échéance, chacune menant à sa fiche. */
export function RemindersCard({ due, items, onOpen }: RemindersCardProps) {
  const hidden = items.length === 0 ? 0 : due - items.length;
  return (
    <section
      aria-labelledby="home-reminders"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h2 id="home-reminders" className="text-lg font-medium">
        {t("home.reminders.title")}
      </h2>
      {items.length === 0 ? (
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
