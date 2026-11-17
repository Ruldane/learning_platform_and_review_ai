import { createBrowserRouter, type RouteObject } from "react-router";
import type { FeatureManifest } from "@/shared/lib/feature";
import { AppLayout } from "./layout/AppLayout";
import { NotFoundPage } from "./pages/NotFoundPage";

/**
 * Routes publiques des manifestes (hors de la mise en page, sans porte), puis la racine `AppLayout`
 * avec les routes de chaque manifeste en enfants et la page introuvable en dernier.
 */
export function buildRoutes(features: FeatureManifest[]): RouteObject[] {
  return [
    ...features.flatMap((feature) => feature.publicRoutes ?? []),
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
