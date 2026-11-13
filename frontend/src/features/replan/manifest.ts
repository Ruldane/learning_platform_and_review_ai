import type { FeatureManifest } from "@/shared/lib/feature";
import { ReplanPage } from "./pages/ReplanPage";

/**
 * Replanification d'un programme : hors navigation, on y arrive par le bouton « Replanifier » du
 * programme, par son bandeau ou par le lien du Stratège (`artifact.ready`).
 */
export const replanManifest: FeatureManifest = {
  id: "replan",
  routes: [{ path: "apprendre/programme/:programId/replanification", Component: ReplanPage }],
};
