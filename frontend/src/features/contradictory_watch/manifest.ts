import type { FeatureManifest } from "@/shared/lib/feature";

export const contradictoryWatchManifest: FeatureManifest = {
  id: "contradictory_watch",
  routes: [
    {
      path: "etudier/veille-contradictoire",
      lazy: async () => ({
        Component: (await import("./pages/WatchPage")).WatchPage,
      }),
    },
    {
      path: "etudier/veille-contradictoire/:experimentId",
      lazy: async () => ({
        Component: (await import("./pages/WatchPage")).WatchDetailPage,
      }),
    },
  ],
  nav: [
    {
      section: "study",
      labelKey: "contradictoryWatch.title",
      path: "/etudier/veille-contradictoire",
      order: 7.5,
    },
  ],
};
