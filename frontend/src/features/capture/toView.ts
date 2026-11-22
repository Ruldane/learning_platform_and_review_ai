import { ideGhostPath, quizGhostPath } from "@/shared/lib/ghostPanels";
import { studySessionPath } from "@/shared/lib/studyRoutes";
import type { JournalEntryView } from "./components/viewTypes";
import type { JournalEntryOut } from "./types";

export function toEntryView(entry: JournalEntryOut): JournalEntryView {
  const {
    quiz_id: quizId,
    quiz_attempt_id: attemptId,
    ide_session_id: ideId,
    ide_run_id: runId,
  } = entry.links;
  const practicePath = ideId && runId ? ideGhostPath(ideId, runId) : undefined;
  return {
    id: entry.id,
    kind: entry.kind,
    text: entry.text,
    occurredOn: entry.occurred_on,
    studySessionPath: entry.links.study_session_id
      ? studySessionPath(entry.links.study_session_id, entry.links.study_session_kind)
      : null,
    practicePath: quizId && attemptId ? quizGhostPath(quizId, attemptId) : practicePath,
    memoryItemId: entry.links.memory_item_id,
  };
}
