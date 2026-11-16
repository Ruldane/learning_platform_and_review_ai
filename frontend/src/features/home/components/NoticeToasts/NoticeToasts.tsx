import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { NoticeView } from "../viewTypes";

/** Nombre maximal de notifications montrées en même temps. */
const MAX_NOTICES = 3;

interface NoticeToastsProps {
  notices: NoticeView[];
  onDismiss: (id: string) => void;
}

/**
 * Les notifications de fond : une région `aria-live="polite"` toujours présente (un lecteur d'écran
 * n'annonce que ce qui s'ajoute à une région déjà là), trois notifications au plus, chacune avec
 * son bouton « Fermer ». Le délai de disparition (8 s) est celui de l'appelant.
 */
export function NoticeToasts({ notices, onDismiss }: NoticeToastsProps) {
  return (
    <div
      role="region"
      aria-live="polite"
      aria-label={t("home.notices.label")}
      className="pointer-events-none fixed right-4 bottom-4 z-40 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2"
    >
      {notices.slice(0, MAX_NOTICES).map((notice) => (
        <div
          key={notice.id}
          className="pointer-events-auto flex flex-col gap-1 rounded-xl border bg-card p-3 text-sm shadow-lg motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
        >
          <p className="font-medium">{notice.title}</p>
          {notice.detail ? <p className="text-muted-foreground">{notice.detail}</p> : null}
          <Button
            variant="ghost"
            size="sm"
            className="self-end"
            aria-label={t("home.notices.dismissNamed", { title: notice.title })}
            onClick={() => onDismiss(notice.id)}
          >
            {t("home.notices.dismiss")}
          </Button>
        </div>
      ))}
    </div>
  );
}
