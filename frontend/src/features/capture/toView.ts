import { studySessionPath } from "@/shared/lib/studyRoutes";
import type { JournalEntryView } from "./components/viewTypes";
import type { JournalEntryOut } from "./types";

export function toEntryView(entry: JournalEntryOut): JournalEntryView {
  return {
    id: entry.id,
    kind: entry.kind,
    text: entry.text,
    occurredOn: entry.occurred_on,
    studySessionPath: entry.links.study_session_id
      ? studySessionPath(entry.links.study_session_id, entry.links.study_session_kind)
      : null,
    memoryItemId: entry.links.memory_item_id,
  };
}
