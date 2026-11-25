import { Children, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { useStickToBottom } from "./useStickToBottom";

interface ChatThreadProps {
  children: ReactNode;
  label: string;
  emptyText: string;
  footer?: ReactNode;
  /** Changes when a reply in progress or the thread footer updates. */
  scrollSignal?: string;
}

export function ChatThread({ children, label, emptyText, footer, scrollSignal }: ChatThreadProps) {
  const count = Children.count(children);
  const { ref, onScroll, jump, unread } = useStickToBottom(count, scrollSignal);
  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div
        ref={ref}
        role="log"
        tabIndex={0}
        aria-label={label}
        onScroll={onScroll}
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3"
      >
        {count === 0 ? <p className="text-sm text-muted-foreground">{emptyText}</p> : null}
        <ol className="flex flex-col gap-3">{children}</ol>
        {footer}
      </div>
      {unread ? (
        <Button
          type="button"
          size="sm"
          className="absolute bottom-2 left-1/2 -translate-x-1/2 shadow-md"
          onClick={jump}
        >
          {t("chat.newMessages")}
        </Button>
      ) : null}
    </div>
  );
}
