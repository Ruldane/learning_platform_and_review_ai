import { t } from "@/shared/i18n/t";
import { NoticeToast } from "../NoticeToast";
import type { NoticeView } from "../viewTypes";

/** Nombre maximal de notifications montrées en même temps. */
const MAX_NOTICES = 3;

const noHold = () => undefined;

interface NoticeToastsProps {
  notices: NoticeView[];
  onDismiss: (id: string) => void;
  /** Une notification est survolée ou a le focus (`true`), ou ne l'est plus (`false`) : son délai attend. */
  onHold?: (id: string, held: boolean) => void;
}

/**
 * Les notifications de fond : une région `aria-live="polite"` toujours présente (un lecteur d'écran
 * n'annonce que ce qui s'ajoute à une région déjà là), trois notifications au plus, chacune avec
 * son bouton « Fermer ». Le délai de disparition (8 s) est celui de l'appelant, en pause au survol
 * et au focus.
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
