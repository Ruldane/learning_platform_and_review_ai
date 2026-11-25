import type { FeatureManifest } from "@/shared/lib/feature";
import { ProofPacketsPage } from "./pages/ProofPacketsPage";

export const proofPacketsManifest: FeatureManifest = {
  id: "proof_packets",
  routes: [{ path: "career/evidence", Component: ProofPacketsPage }],
  nav: [
    { section: "career", labelKey: "proofPackets.title", path: "/career/evidence", order: 5.8 },
  ],
};
