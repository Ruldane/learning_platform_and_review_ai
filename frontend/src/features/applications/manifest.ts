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
 * Applications (SPEC 6, « Candidatures » section of the navigation): the tracking (board
 * or table) with the record in a drawer on top, reminders (badge = reminders due), the
 * new record (by hand or in one sentence), the kit (7.14), the mock interview (7.15,
 * from a record or free). The simulated committee is under
 * `/applications/:applicationId/committee`.
 */
export const applicationsManifest: FeatureManifest = {
  id: "applications",
  routes: [
    {
      path: "applications",
      Component: BoardPage,
      // Eight card columns: the page takes the full width.
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
