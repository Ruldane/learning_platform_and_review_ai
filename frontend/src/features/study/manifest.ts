import type { FeatureManifest } from "@/shared/lib/feature";
import { StudyTopbarSlot } from "./StudyTopbarSlot";
import { StudyHomePage } from "./pages/StudyHomePage";
import { StudySessionPage } from "./pages/StudySessionPage";

/**
 * Study, 1st entry: the guided session (day's block, Tutor, timer, summary; SPEC 3.7). The
 * session fills the shell's full width (debate left, table right). The streak and
 * the week's hours are shown in the top bar.
 */
export const studyManifest: FeatureManifest = {
  id: "study",
  routes: [
    { path: "study/session", Component: StudyHomePage },
    { path: "study/session/:studyId", Component: StudySessionPage, handle: { wide: true } },
  ],
  nav: [{ section: "study", labelKey: "study.nav.session", path: "/study/session", order: 1 }],
  shell: { topbar: StudyTopbarSlot },
};
