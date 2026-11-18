import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ChatItem } from "../chatItems";
import { ChatMessage } from "../ChatMessage";
import { PendingMessage } from "./PendingMessage";
import { useStickToBottom } from "./useStickToBottom";

interface ChatThreadProps {
  items: ChatItem[];
  /** Une décision sur une proposition est en cours. */
  busy: boolean;
  onAccept: (noteId: string) => void;
  onReject: (noteId: string) => void;
  /** Sous le dernier message : « Le professeur écrit… », raison d'un refus, erreur. */
  footer: ReactNode;
  /** Change quand le pied du fil change (le fil redescend aussi pour lui). */
  footerKey: string;
}

/**
 * Le fil de la conversation : il défile **dans le panneau**, pas dans la page. Il descend au
 * dernier message à chaque arrivée, sauf si January est remontée lire : un bouton « Nouveaux
 * messages » apparaît alors.
 */
export function ChatThread({ items, busy, onAccept, onReject, footer, footerKey }: ChatThreadProps) {
  const { ref, onScroll, jump, unread } = useStickToBottom(items.length, footerKey);
  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div
        ref={ref}
        role="log"
        tabIndex={0}
        aria-label={t("ide.chat.thread")}
        onScroll={onScroll}
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3"
      >
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("ide.teacher.empty")}</p>
        ) : null}
        <ol className="flex flex-col gap-3">
          {items.map((item) =>
            item.type === "pending" ? (
              <PendingMessage key={item.id} text={item.text} />
            ) : (
              <ChatMessage
                key={item.id}
                note={item.note}
                mine={item.mine}
                tag={item.tag}
                busy={busy}
                onAccept={() => onAccept(item.id)}
                onReject={() => onReject(item.id)}
              />
            ),
          )}
        </ol>
        {footer}
      </div>
      {unread ? (
        <Button
          type="button"
          size="sm"
          className="absolute bottom-2 left-1/2 -translate-x-1/2 shadow-md"
          onClick={jump}
        >
          {t("ide.chat.newMessages")}
        </Button>
      ) : null}
    </div>
  );
}
