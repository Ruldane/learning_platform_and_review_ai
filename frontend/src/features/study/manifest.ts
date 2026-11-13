import type { FeatureManifest } from "@/shared/lib/feature";
import { StudyTopbarSlot } from "./StudyTopbarSlot";
import { StudyHomePage } from "./pages/StudyHomePage";
import { StudySessionPage } from "./pages/StudySessionPage";

/**
 * Étudier, 1re entrée : la session guidée (bloc du jour, Tuteur, minuteur, bilan ; SPEC 3.7). La
 * session occupe toute la largeur de la coquille (débat à gauche, tableau à droite). La série et
 * les heures de la semaine s'affichent dans la barre du haut.
 */
export const studyManifest: FeatureManifest = {
  id: "study",
  routes: [
    { path: "etudier/session", Component: StudyHomePage },
    { path: "etudier/session/:studyId", Component: StudySessionPage, handle: { wide: true } },
  ],
  nav: [{ section: "study", labelKey: "study.nav.session", path: "/etudier/session", order: 1 }],
  shell: { topbar: StudyTopbarSlot },
};
