import { useId, type ReactNode } from "react";
import { cn } from "@/shared/lib/utils";
import { ChatMarkdown } from "../ChatMarkdown";

interface ChatMessageProps {
  id?: string;
  author: string;
  label: string;
  content: string;
  tag?: string | null;
  context?: string | null;
  muted?: boolean;
  allowLinks?: boolean;
  children?: ReactNode;
}

export function ChatMessage({
  id,
  author,
  label,
  content,
  tag,
  context,
  muted,
  allowLinks,
  children,
}: ChatMessageProps) {
  const labelId = useId();
  const mine = author === "user";
  return (
    <li className={cn("flex", mine ? "justify-end" : "justify-start")}>
      <article
        id={id}
        aria-labelledby={labelId}
        data-author={author}
        className={cn(
          "flex max-w-[90%] flex-col gap-1 rounded-2xl border px-3 py-2",
          mine ? "border-transparent bg-accent text-accent-foreground" : "border-border bg-card",
          muted && "opacity-60",
        )}
      >
        <p id={labelId} className="text-xs font-medium">
          {label}
          {tag ? (
            <>
              {" "}
              <span className="font-normal text-muted-foreground">· {tag}</span>
            </>
          ) : null}
        </p>
        {context ? <p className="text-xs text-muted-foreground">{context}</p> : null}
        {mine ? (
          <p className="text-sm whitespace-pre-wrap">{content}</p>
        ) : (
          <ChatMarkdown allowLinks={allowLinks}>{content}</ChatMarkdown>
        )}
        {children}
      </article>
    </li>
  );
}
