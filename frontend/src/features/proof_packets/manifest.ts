import type { FeatureManifest } from "@/shared/lib/feature";
import { ProofPacketsPage } from "./pages/ProofPacketsPage";

export const proofPacketsManifest: FeatureManifest = {
  id: "proof_packets",
  routes: [{ path: "carriere/preuves", Component: ProofPacketsPage }],
  nav: [{ section: "career", labelKey: "proofPackets.title", path: "/carriere/preuves", order: 5.8 }],
};
