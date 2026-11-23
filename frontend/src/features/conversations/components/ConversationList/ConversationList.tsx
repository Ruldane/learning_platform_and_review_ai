import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ConversationSearch } from "./ConversationSearch";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ConversationRemoval } from "./ConversationRemoval";
import { ConversationEntries } from "./ConversationEntries";
import { ManageConversation } from "./ManageConversation";
import type { ListProps } from "./types";

function matches(text: string, search: string) {
  const normalize = (value: string) =>
    value
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLowerCase();
  return normalize(text).includes(normalize(search.trim()));
}

export function ConversationList(props: ListProps) {
  const { entries, pending, selected, busy, error, newRef, onCreate, onAction, onSelect } = props;
  const [search, setSearch] = useState("");
  const searchId = useId();
  const headingId = useId();
  const Heading = props.heading ?? "h2";
  const active = entries.find((entry) => entry.id === selected);
  const filtered = entries.filter((entry) => matches(entry.title, search));
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
      <ConversationSearch id={searchId} value={search} onChange={setSearch} />
      {error && <InlineError message={error} />}
      {pending ? (
        <p role="status" className="text-sm">
          {t("conversations.loading")}
        </p>
      ) : null}
      {!pending && !error && filtered.length === 0 ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t(search.trim() ? "conversations.list.noMatches" : "conversations.list.noThreads")}
        </p>
      ) : null}
      <ConversationEntries entries={filtered} selected={selected} busy={busy} onSelect={onSelect} />
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
