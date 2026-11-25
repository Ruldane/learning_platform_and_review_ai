import type { FeatureManifest } from "@/shared/lib/feature";

export const codeTrialManifest: FeatureManifest = {
  id: "code_trial",
  routes: [
    {
      path: "code/:sessionId/trial/:trialId?",
      lazy: async () => ({ Component: (await import("./pages/CodeTrialPage")).CodeTrialPage }),
    },
  ],
};
