import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ConversationSearch } from "./ConversationSearch";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ConversationRemoval } from "./ConversationRemoval";
import { ConversationEntries } from "./ConversationEntries";
import { ManageConversation } from "./ManageConversation";
import type { ListProps } from "./types";

export function ConversationList(props: ListProps) {
  const { entries, pending, selected, busy, error, newRef, onCreate, onAction, onSelect } = props;
  const { visibleEntries, search, onSearch } = props;
  const searchId = useId();
  const headingId = useId();
  const Heading = props.heading ?? "h2";
  const active = entries.find((entry) => entry.id === selected);
  return (
    <aside
      aria-labelledby={headingId}
      className="flex min-w-0 flex-col gap-3 self-start rounded-xl border border-border p-3"
    >
      <Heading id={headingId} className="font-semibold">
        {t("conversations.list.label")}
      </Heading>
      <Button ref={newRef} type="button" size="sm" disabled={busy} onClick={onCreate}>
        {t("conversations.list.create")}
      </Button>
      <ConversationSearch id={searchId} value={search} onChange={onSearch} />
      {error && <InlineError message={error} />}
      {pending ? (
        <p role="status" className="text-sm">
          {t("conversations.loading")}
        </p>
      ) : null}
      {!pending && !error && visibleEntries.length === 0 ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t(search.trim() ? "conversations.list.noMatches" : "conversations.list.noThreads")}
        </p>
      ) : null}
      <ConversationEntries
        entries={visibleEntries}
        selected={selected}
        busy={busy}
        onSelect={onSelect}
      />
      {active && (
        <ManageConversation key={active.id} entry={active} busy={busy} onAction={onAction} />
      )}
      {entries.length > 0 && (
        <ConversationRemoval
          action="wipe"
          busy={busy}
          onConfirm={() => onAction({ kind: "wipe" })}
        />
      )}
    </aside>
  );
}
