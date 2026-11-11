import { createBrowserRouter, type RouteObject } from "react-router";
import type { FeatureManifest } from "@/shared/lib/feature";
import { AppLayout } from "./layout/AppLayout";
import { NotFoundPage } from "./pages/NotFoundPage";

/** Racine `AppLayout`, routes de chaque manifeste en enfants, page introuvable en dernier. */
export function buildRoutes(features: FeatureManifest[]): RouteObject[] {
  return [
    {
      path: "/",
      Component: AppLayout,
      children: [
        ...features.flatMap((feature) => feature.routes),
        { path: "*", Component: NotFoundPage },
      ],
    },
  ];
}

export function buildRouter(features: FeatureManifest[]) {
  return createBrowserRouter(buildRoutes(features));
}
