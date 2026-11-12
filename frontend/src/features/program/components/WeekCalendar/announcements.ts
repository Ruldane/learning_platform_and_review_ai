import type { Announcements } from "@dnd-kit/core";
import { t } from "@/shared/i18n/t";
import { longDay } from "@/shared/lib/format";
import type { WeekView } from "../viewTypes";

/** Annonces du glisser-déposer pour les lecteurs d'écran, en français. */
export function makeAnnouncements(week: WeekView): Announcements {
  const tasks = week.days.flatMap((day) => day.tasks);
  const titleOf = (id: string | number) =>
    tasks.find((task) => task.id === String(id))?.title ?? "";
  const dayOf = (id: string | number) => longDay(String(id));
  const home = (id: string | number) => tasks.find((task) => task.id === String(id))?.plannedDate;
  return {
    onDragStart: ({ active }) =>
      t("program.calendar.announce.start", { title: titleOf(active.id) }),
    onDragOver: ({ active, over }) =>
      over
        ? t("program.calendar.announce.over", { title: titleOf(active.id), day: dayOf(over.id) })
        : t("program.calendar.announce.overNothing", { title: titleOf(active.id) }),
    onDragEnd: ({ active, over }) =>
      over
        ? t("program.calendar.announce.end", { title: titleOf(active.id), day: dayOf(over.id) })
        : t("program.calendar.announce.endNothing", { title: titleOf(active.id) }),
    onDragCancel: ({ active }) =>
      t("program.calendar.announce.cancel", {
        title: titleOf(active.id),
        day: dayOf(home(active.id) ?? ""),
      }),
  };
}
