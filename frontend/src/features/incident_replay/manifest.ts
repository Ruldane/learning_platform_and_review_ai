import type { FeatureManifest } from "@/shared/lib/feature";

export const incidentReplayManifest: FeatureManifest = {
  id: "incident_replay",
  routes: [
    {
      path: "study/incident-replay",
      lazy: async () => ({
        Component: (await import("./pages/ReplayPage")).ReplayPage,
      }),
    },
    {
      path: "study/incident-replay/:replayId",
      lazy: async () => ({
        Component: (await import("./pages/ReplayPage")).ReplayDetailPage,
      }),
    },
  ],
  nav: [
    {
      section: "study",
      labelKey: "incidentReplay.title",
      path: "/study/incident-replay",
      order: 7.6,
    },
  ],
};
