import type { StudyModeView } from "../../components/viewTypes";
import type { useStartStudy } from "../../hooks/useStartStudy";

/** What the two starts (day's block, chosen lesson) share: the mode and the launcher. */
export interface StartProps {
  mode: StudyModeView;
  onMode: (mode: StudyModeView) => void;
  starter: ReturnType<typeof useStartStudy>;
  /** Session already open, to resume. */
  openSessionId: string | null;
}
