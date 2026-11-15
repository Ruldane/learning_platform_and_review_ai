import { t } from "@/shared/i18n/t";
import type { FeatureManifest } from "@/shared/lib/feature";
import { useDueCount } from "./hooks/useDueCount";
import { ApplicationDrawer } from "./pages/ApplicationDrawer";
import { BoardPage } from "./pages/BoardPage";
import { FreeInterviewPage } from "./pages/FreeInterviewPage";
import { InterviewPage } from "./pages/InterviewPage";
import { KitPage } from "./pages/KitPage";
import { NewApplicationPage } from "./pages/NewApplication";
import { RemindersPage } from "./pages/RemindersPage";

/**
 * Les candidatures (SPEC 6, section « Candidatures » de la navigation) : le suivi (tableau de suivi
 * ou tableau) avec la fiche en tiroir par-dessus, les relances (pastille = relances dues), la
 * nouvelle fiche (à la main ou en une phrase), le kit d'une candidature (7.14), l'entretien blanc (7.15,
 * depuis une fiche ou libre). La page du comité (7.16) s'ajoute sous `/candidatures/:applicationId/…`.
 */
export const applicationsManifest: FeatureManifest = {
  id: "applications",
  routes: [
    {
      path: "candidatures",
      Component: BoardPage,
      // Huit colonnes de cartes : la page prend toute la largeur.
      handle: { wide: true },
      children: [{ path: ":applicationId", Component: ApplicationDrawer }],
    },
    { path: "candidatures/relances", Component: RemindersPage },
    { path: "candidatures/nouvelle", Component: NewApplicationPage },
    { path: "candidatures/entretien", Component: FreeInterviewPage },
    { path: "candidatures/:applicationId/kit", Component: KitPage },
    { path: "candidatures/:applicationId/entretien", Component: InterviewPage },
  ],
  nav: [
    {
      section: "applications",
      labelKey: "applications.nav.board",
      path: "/candidatures",
      order: 1,
    },
    {
      section: "applications",
      labelKey: "applications.nav.reminders",
      path: "/candidatures/relances",
      order: 2,
      useBadge: useDueCount,
      badgeLabel: (count) =>
        t(`applications.nav.dueBadge.${count === 1 ? "one" : "many"}`, { count }),
    },
    {
      section: "applications",
      labelKey: "applications.nav.interview",
      path: "/candidatures/entretien",
      order: 3,
    },
  ],
};
