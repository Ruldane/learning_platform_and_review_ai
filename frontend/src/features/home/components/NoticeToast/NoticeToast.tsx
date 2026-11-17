import { useEffect, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { NoticeView } from "../viewTypes";

interface NoticeToastProps {
  notice: NoticeView;
  onDismiss: (id: string) => void;
  /** Le pointeur est dessus ou le focus dedans (`true`), ou plus rien de tout cela (`false`). */
  onHold: (id: string, held: boolean) => void;
}

/**
 * Une notification de fond : titre, détail et « Fermer ». Tant que le pointeur la survole ou que le
 * focus est dedans, elle se déclare tenue (`onHold`) : sa disparition attend qu'on l'ait lue.
 */
export function NoticeToast({ notice, onDismiss, onHold }: NoticeToastProps) {
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const held = hovered || focused;
  const { id } = notice;
  useEffect(() => {
    if (!held) return;
    onHold(id, true);
    return () => onHold(id, false);
  }, [held, id, onHold]);

  return (
    <div
      data-notice
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false);
      }}
      className="pointer-events-auto flex flex-col gap-1 rounded-xl border bg-card p-3 text-sm shadow-lg motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
    >
      <p className="font-medium">{notice.title}</p>
      {notice.detail ? <p className="text-muted-foreground">{notice.detail}</p> : null}
      <Button
        variant="ghost"
        size="sm"
        className="self-end"
        aria-label={t("home.notices.dismissNamed", { title: notice.title })}
        onClick={() => onDismiss(id)}
      >
        {t("home.notices.dismiss")}
      </Button>
    </div>
  );
}
