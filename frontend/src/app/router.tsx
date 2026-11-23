import { createBrowserRouter, type RouteObject } from "react-router";
import type { FeatureManifest } from "@/shared/lib/feature";
import { AppLayout } from "./layout/AppLayout";
import { buildDestinations, descriptionKey, sectionLanding, type Hub } from "./navigation";
import { DestinationCards, NavigationPage, SettingsTabs } from "./pages/NavigationPage";
import { NotFoundPage } from "./pages/NotFoundPage";

const HUBS: Hub[] = ["learn", "code", "memory", "career"];

function landingRoutes(features: FeatureManifest[]): RouteObject[] {
  const cards = buildDestinations(features);
  const hubs = HUBS.map((section) => ({
    path: sectionLanding(section).path,
    element: <NavigationPage section={section}>
      <DestinationCards cards={cards.filter((card) => card.section === section)} />
    </NavigationPage>,
  }));
  return [...hubs, {
    path: sectionLanding("settings").path,
    element: <NavigationPage section="settings">
      <SettingsTabs cards={cards.filter((card) => card.section === "settings")} />
    </NavigationPage>,
  }];
}

function withDescription(route: RouteObject, feature: FeatureManifest): RouteObject {
  const description = feature.id === "home" ? undefined : descriptionKey(feature.id);
  return description ? { ...route, handle: { ...route.handle, description } } : route;
}

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
        ...features.flatMap((feature) => feature.routes.map((route) => withDescription(route, feature))),
        ...landingRoutes(features),
        { path: "*", Component: NotFoundPage },
      ],
    },
  ];
}

export function buildRouter(features: FeatureManifest[]) {
  return createBrowserRouter(buildRoutes(features));
}
