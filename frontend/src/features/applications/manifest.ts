import { t } from "@/shared/i18n/t";
import type { FeatureManifest } from "@/shared/lib/feature";
import { useDueCount } from "./hooks/useDueCount";
import { ApplicationDrawer } from "./pages/ApplicationDrawer";
import { BoardPage } from "./pages/BoardPage";
import { CommitteePage } from "./pages/CommitteePage";
import { FreeInterviewPage } from "./pages/FreeInterviewPage";
import { InterviewPage } from "./pages/InterviewPage";
import { SystemDesignPage } from "./pages/SystemDesignPage";
import { KitPage } from "./pages/KitPage";
import { NewApplicationPage } from "./pages/NewApplication";
import { RemindersPage } from "./pages/RemindersPage";

/**
 * Les candidatures (SPEC 6, section « Candidatures » de la navigation) : le suivi (tableau de suivi
 * ou tableau) avec la fiche en tiroir par-dessus, les relances (pastille = relances dues), la
 * nouvelle fiche (à la main ou en une phrase), le kit d'une candidature (7.14), l'entretien blanc (7.15,
 * depuis une fiche ou libre). Le comité simulé est sous `/applications/:applicationId/committee`.
 */
export const applicationsManifest: FeatureManifest = {
  id: "applications",
  routes: [
    {
      path: "applications",
      Component: BoardPage,
      // Huit colonnes de cartes : la page prend toute la largeur.
      handle: { wide: true },
      children: [{ path: ":applicationId", Component: ApplicationDrawer }],
    },
    { path: "applications/reminders", Component: RemindersPage },
    { path: "applications/new", Component: NewApplicationPage },
    { path: "applications/interview", Component: FreeInterviewPage },
    {
      path: "applications/system-design/:interviewId?",
      Component: SystemDesignPage,
      handle: { wide: true },
    },
    { path: "applications/:applicationId/kit", Component: KitPage },
    { path: "applications/:applicationId/interview", Component: InterviewPage },
    { path: "applications/:applicationId/committee", Component: CommitteePage },
  ],
  nav: [
    {
      section: "applications",
      labelKey: "applications.nav.board",
      path: "/applications",
      order: 1,
    },
    {
      section: "applications",
      labelKey: "applications.nav.reminders",
      path: "/applications/reminders",
      order: 2,
      useBadge: useDueCount,
      badgeLabel: (count) =>
        t(`applications.nav.dueBadge.${count === 1 ? "one" : "many"}`, { count }),
    },
    {
      section: "applications",
      labelKey: "applications.nav.interview",
      path: "/applications/interview",
      order: 3,
    },
  ],
};
