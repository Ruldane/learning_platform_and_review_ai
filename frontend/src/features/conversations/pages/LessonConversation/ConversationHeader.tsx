import { useEffect, useRef } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ConversationHeaderProps {
  id: string;
  lessonId: string;
  excerpt: string | null;
  onClose: () => void;
}

function usePanelFocus(onClose: () => void) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  useEffect(() => {
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented) onClose();
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [onClose]);
  return heading;
}

export function ConversationHeader({ id, lessonId, excerpt, onClose }: ConversationHeaderProps) {
  const heading = usePanelFocus(onClose);
  return (
    <>
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h2
          id={id}
          ref={heading}
          tabIndex={-1}
          className="text-lg font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {t("conversations.title")}
        </h2>
        <Button type="button" variant="outline" onClick={onClose}>
          {t("conversations.close")}
        </Button>
      </header>
      {excerpt ? (
        <blockquote className="mx-4 mt-3 max-h-24 overflow-y-auto border-l-2 px-3 text-sm">
          {excerpt}
        </blockquote>
      ) : null}
      <Link
        to={`/etudier/session?lecon=${encodeURIComponent(lessonId)}`}
        className="mx-4 my-2 self-start text-sm underline"
        state={excerpt ? { lessonId, question: excerpt } : undefined}
      >
        {t("conversations.study")}
      </Link>
    </>
  );
}
