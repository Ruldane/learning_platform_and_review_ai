import { t } from "@/shared/i18n/t";
import { NoticeToast } from "../NoticeToast";
import type { NoticeView } from "../viewTypes";

/** Maximum number of notifications shown at once. */
const MAX_NOTICES = 3;

const noHold = () => undefined;

interface NoticeToastsProps {
  notices: NoticeView[];
  onDismiss: (id: string) => void;
  /**
   * A notification is hovered or focused (`true`), or no longer is (`false`): its delay
   * attend.
   */
  onHold?: (id: string, held: boolean) => void;
}

/**
 * Background notifications: an `aria-live="polite"` region always present (a screen reader
 * only announces what is added to a region already there), at most three notifications, each with
 * its « Fermer » button. The removal delay (8 s) is the caller's, paused on hover
 * and focus.
 */
export function NoticeToasts({ notices, onDismiss, onHold = noHold }: NoticeToastsProps) {
  return (
    <div
      role="region"
      aria-live="polite"
      aria-label={t("home.notices.label")}
      className="pointer-events-none fixed right-4 bottom-4 z-40 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2"
    >
      {notices.slice(0, MAX_NOTICES).map((notice) => (
        <NoticeToast key={notice.id} notice={notice} onDismiss={onDismiss} onHold={onHold} />
      ))}
    </div>
  );
}
