import type { FeatureManifest } from "@/shared/lib/feature";
import { CompatibleOfferPage } from "./pages/CompatibleOfferPage";

export const compatibleOffersManifest: FeatureManifest = {
  id: "compatible_offers",
  routes: [{ path: "career/compatible-offers/:runId/:ref", Component: CompatibleOfferPage }],
};
