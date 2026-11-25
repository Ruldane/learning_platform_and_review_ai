import type { FeatureManifest } from "@/shared/lib/feature";

export const meetingModulesManifest: FeatureManifest = {
  id: "meeting_modules",
  routes: [
    {
      path: "study/meeting-modules",
      lazy: async () => ({
        Component: (await import("./pages/MeetingPages")).MeetingLibrary,
      }),
    },
    {
      path: "study/meeting-modules/:moduleId",
      lazy: async () => ({
        Component: (await import("./pages/MeetingPages")).MeetingDetail,
      }),
    },
  ],
  nav: [
    {
      section: "study",
      labelKey: "meetingModules.title",
      path: "/study/meeting-modules",
      order: 7.9,
    },
  ],
};
