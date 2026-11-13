import type { JournalEntryView } from "./components/viewTypes";
import type { JournalEntryOut } from "./types";

export function toEntryView(entry: JournalEntryOut): JournalEntryView {
  return {
    id: entry.id,
    kind: entry.kind,
    text: entry.text,
    occurredOn: entry.occurred_on,
    studySessionId: entry.links.study_session_id,
    memoryItemId: entry.links.memory_item_id,
  };
}
