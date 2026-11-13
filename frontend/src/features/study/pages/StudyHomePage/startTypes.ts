import type { StudyModeView } from "../../components/viewTypes";
import type { useStartStudy } from "../../hooks/useStartStudy";

/** Ce que les deux départs (bloc du jour, leçon choisie) se partagent : le mode et le lanceur. */
export interface StartProps {
  mode: StudyModeView;
  onMode: (mode: StudyModeView) => void;
  starter: ReturnType<typeof useStartStudy>;
  /** Session déjà ouverte, à reprendre. */
  openSessionId: string | null;
}
