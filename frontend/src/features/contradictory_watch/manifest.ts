import type { FeatureManifest } from "@/shared/lib/feature";

export const contradictoryWatchManifest: FeatureManifest = {
  id: "contradictory_watch",
  routes: [
    {
      path: "study/contradictory-watch",
      lazy: async () => ({
        Component: (await import("./pages/WatchPage")).WatchPage,
      }),
    },
    {
      path: "study/contradictory-watch/:experimentId",
      lazy: async () => ({
        Component: (await import("./pages/WatchPage")).WatchDetailPage,
      }),
    },
  ],
  nav: [
    {
      section: "study",
      labelKey: "contradictoryWatch.title",
      path: "/study/contradictory-watch",
      order: 7.5,
    },
  ],
};
