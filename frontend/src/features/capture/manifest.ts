import type { FeatureManifest } from "@/shared/lib/feature";
import { CaptureOverlay } from "./CaptureOverlay";
import { CaptureTopbarButton } from "./CaptureTopbarButton";
import { JournalPage } from "./pages/JournalPage";

/**
 * Quick capture and journal (SPEC F18). Capture is the app's global action: a
 * top bar button and the Ctrl+K / Cmd+K shortcut open its dialog (`overlay`).
 * The journal is the 4th entry of the Study section.
 */
export const captureManifest: FeatureManifest = {
  id: "capture",
  routes: [{ path: "study/journal", Component: JournalPage }],
  nav: [{ section: "study", labelKey: "capture.nav.journal", path: "/study/journal", order: 4 }],
  shell: { topbar: CaptureTopbarButton, overlay: CaptureOverlay },
};
