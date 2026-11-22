import type { FeatureManifest } from "@/shared/lib/feature";

export const incidentReplayManifest: FeatureManifest = {
  id: "incident_replay",
  routes: [
    {
      path: "etudier/replay-incident",
      lazy: async () => ({
        Component: (await import("./pages/ReplayPage")).ReplayPage,
      }),
    },
    {
      path: "etudier/replay-incident/:replayId",
      lazy: async () => ({
        Component: (await import("./pages/ReplayPage")).ReplayDetailPage,
      }),
    },
  ],
  nav: [
    {
      section: "study",
      labelKey: "incidentReplay.title",
      path: "/etudier/replay-incident",
      order: 7.6,
    },
  ],
};
