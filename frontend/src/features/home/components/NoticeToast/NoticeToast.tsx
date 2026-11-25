import { useEffect, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { NoticeView } from "../viewTypes";

interface NoticeToastProps {
  notice: NoticeView;
  onDismiss: (id: string) => void;
  /** The pointer is over it or focus is inside (`true`), or neither (`false`). */
  onHold: (id: string, held: boolean) => void;
}

/**
 * A background notification: title, detail and « Fermer ». While the pointer hovers it or the
 * focus is inside, it is held (`onHold`): its removal waits until it has been read.
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
