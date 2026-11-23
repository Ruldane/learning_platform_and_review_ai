import { ConversationRemoval } from "./ConversationRemoval";
import { ConversationTitle } from "./ConversationTitle";
import type { Entry, ListProps } from "./types";

export function ManageConversation({
  entry,
  busy,
  onAction,
}: {
  entry: Entry;
  busy: boolean;
  onAction: ListProps["onAction"];
}) {
  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3">
      <ConversationTitle
        title={entry.title}
        busy={busy}
        onSave={(title) => onAction({ kind: "rename", id: entry.id, title })}
      />
      <div className="flex flex-wrap gap-2">
        <ConversationRemoval
          action="clear"
          busy={busy}
          onConfirm={() => onAction({ kind: "clear", id: entry.id })}
        />
        <ConversationRemoval
          action="delete"
          busy={busy}
          onConfirm={() => onAction({ kind: "delete", id: entry.id })}
        />
      </div>
    </div>
  );
}
