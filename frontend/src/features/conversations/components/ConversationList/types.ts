import type { Ref } from "react";

export type Entry = { id: string; title: string };
export type ConversationListAction =
  | { kind: "rename"; id: string; title: string }
  | { kind: "clear" | "delete"; id: string }
  | { kind: "wipe" };

export interface ListProps {
  heading?: "h2" | "h3";
  entries: Entry[];
  visibleEntries: Entry[];
  search: string;
  onSearch: (search: string) => void;
  selected: string | null;
  pending: boolean;
  busy: boolean;
  error?: string;
  newRef: Ref<HTMLButtonElement>;
  onCreate: () => void;
  onSelect: (id: string) => void;
  onAction: (action: ConversationListAction) => void;
}
