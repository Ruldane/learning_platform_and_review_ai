import type { FeatureManifest } from "@/shared/lib/feature";
import { CaptureOverlay } from "./CaptureOverlay";
import { CaptureTopbarButton } from "./CaptureTopbarButton";
import { JournalPage } from "./pages/JournalPage";

/**
 * Capture rapide et journal (SPEC F18). La capture est l'action globale de l'application : un
 * bouton dans la barre du haut et le raccourci Ctrl+K / Cmd+K ouvrent son dialogue (`overlay`).
 * Le journal est la 4e entrée de la section Étudier.
 */
export const captureManifest: FeatureManifest = {
  id: "capture",
  routes: [{ path: "etudier/journal", Component: JournalPage }],
  nav: [{ section: "study", labelKey: "capture.nav.journal", path: "/etudier/journal", order: 4 }],
  shell: { topbar: CaptureTopbarButton, overlay: CaptureOverlay },
};
