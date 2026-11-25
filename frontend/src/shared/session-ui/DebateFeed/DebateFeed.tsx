import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { getEventRenderer } from "@/shared/realtime/eventRenderers";
import type { FeedItem } from "@/shared/realtime/types";
import { AgentBubble } from "../AgentBubble";
import { UserMessageBubble } from "../UserMessageBubble";

type InterruptItem = Extract<FeedItem, { kind: "interrupt" }>;

interface DebateFeedProps {
  items: FeedItem[];
  /** Question cards are wired in by the page (only it knows the resume action). */
  renderInterrupt: (item: InterruptItem) => ReactNode;
}

function itemKey(item: FeedItem): string {
  switch (item.kind) {
    case "turn":
      return `turn-${item.messageId}`;
    case "event":
      return `event-${item.event.id}`;
    default:
      return `${item.kind}-${item.seq}`;
  }
}

/** Content of a feed item; `null` if nothing renders it (event with no registered component). */
function itemContent(item: FeedItem, renderInterrupt: DebateFeedProps["renderInterrupt"]) {
  switch (item.kind) {
    case "turn":
      return (
        <AgentBubble
          agent={item.agent}
          text={item.text}
          streaming={item.streaming}
          intent={item.intent}
          tools={item.tools}
          citations={item.citations}
        />
      );
    case "user":
      return <UserMessageBubble text={item.text} command={item.command} />;
    case "interrupt":
      return renderInterrupt(item);
    case "event": {
      const Renderer = getEventRenderer(item.event.type);
      return Renderer ? <Renderer event={item.event} /> : null;
    }
  }
}

/** The debate feed: one bubble per turn, user messages, question cards and registered events. */
export function DebateFeed({ items, renderInterrupt }: DebateFeedProps) {
  const entries = items
    .map((item) => ({ key: itemKey(item), content: itemContent(item, renderInterrupt) }))
    .filter((entry) => entry.content !== null);
  if (entries.length === 0) {
    return <p className="text-muted-foreground">{t("session.feed.empty")}</p>;
  }
  return (
    <ol aria-label={t("session.feed.label")} className="flex flex-col gap-3">
      {entries.map((entry) => (
        <li key={entry.key} className="flex flex-col">
          {entry.content}
        </li>
      ))}
    </ol>
  );
}
