import type { FeatureManifest } from "@/shared/lib/feature";
import { CompatibleOfferPage } from "./pages/CompatibleOfferPage";

export const compatibleOffersManifest: FeatureManifest = {
  id: "compatible_offers",
  routes: [{ path: "carriere/offres-compatibles/:runId/:ref", Component: CompatibleOfferPage }],
};
