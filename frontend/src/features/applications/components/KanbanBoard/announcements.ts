import type { Announcements } from "@dnd-kit/core";
import { t } from "@/shared/i18n/t";
import { STATUS_ORDER } from "../viewTypes";
import type { ApplicationView, StatusView } from "../viewTypes";

const isStatus = (id: string | number): id is StatusView =>
  (STATUS_ORDER as readonly string[]).includes(String(id));

/** The name of a status in words, or empty for an area that is not a column. */
export function statusName(id: string | number): string {
  return isStatus(id) ? t(`applications.status.${id}`) : "";
}

/** Drag-and-drop announcements for screen readers, in French. */
export function makeAnnouncements(applications: ApplicationView[]): Announcements {
  const find = (id: string | number) => applications.find((item) => item.id === String(id));
  const titleOf = (id: string | number) => find(id)?.title ?? "";
  return {
    onDragStart: ({ active }) =>
      t("applications.board.announce.start", { title: titleOf(active.id) }),
    onDragOver: ({ active, over }) =>
      over
        ? t("applications.board.announce.over", {
            title: titleOf(active.id),
            status: statusName(over.id),
          })
        : t("applications.board.announce.overNothing", { title: titleOf(active.id) }),
    onDragEnd: ({ active, over }) =>
      over
        ? t("applications.board.announce.end", {
            title: titleOf(active.id),
            status: statusName(over.id),
          })
        : t("applications.board.announce.endNothing", { title: titleOf(active.id) }),
    onDragCancel: ({ active }) =>
      t("applications.board.announce.cancel", {
        title: titleOf(active.id),
        status: statusName(find(active.id)?.status ?? ""),
      }),
  };
}
