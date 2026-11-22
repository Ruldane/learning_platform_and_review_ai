import type { FeatureManifest } from "@/shared/lib/feature";

export const meetingModulesManifest: FeatureManifest = {
  id: "meeting_modules",
  routes: [
    {
      path: "etudier/modules-reunion",
      lazy: async () => ({
        Component: (await import("./pages/MeetingPages")).MeetingLibrary,
      }),
    },
    {
      path: "etudier/modules-reunion/:moduleId",
      lazy: async () => ({
        Component: (await import("./pages/MeetingPages")).MeetingDetail,
      }),
    },
  ],
  nav: [
    {
      section: "study",
      labelKey: "meetingModules.title",
      path: "/etudier/modules-reunion",
      order: 7.9,
    },
  ],
};
