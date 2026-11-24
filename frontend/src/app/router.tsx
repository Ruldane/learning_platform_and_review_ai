import {
  createBrowserRouter,
  generatePath,
  Navigate,
  type RouteObject,
  useLocation,
  useParams,
} from "react-router";
import type { FeatureManifest } from "@/shared/lib/feature";
import { LEGACY_PATHS } from "./legacyPaths";
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

function LegacyRedirect({ destination }: { destination: string }) {
  const { search, hash, state } = useLocation();
  const params = Object.fromEntries(
    Object.entries(useParams()).map(([key, value]) => [key, encodeURIComponent(value ?? "")]),
  );
  const pathname = generatePath(destination, params);
  return <Navigate to={{ pathname, search, hash }} state={state} replace />;
}

function redirectRoutes(routes: Record<string, string> = {}): RouteObject[] {
  return Object.entries(routes).map(([path, destination]) => ({
    path,
    element: <LegacyRedirect destination={destination} />,
  }));
}

function featureRoutes(feature: FeatureManifest): RouteObject[] {
  return [
    ...feature.routes.map((route) => withDescription(route, feature)),
    ...redirectRoutes(feature.legacyRoutes),
  ];
}

/** Mount public routes first, then the pages and redirects protected by the app layout. */
export function buildRoutes(features: FeatureManifest[]): RouteObject[] {
  return [
    ...features.flatMap((feature) => [
      ...(feature.publicRoutes ?? []),
      ...redirectRoutes(feature.legacyPublicRoutes),
    ]),
    {
      path: "/",
      Component: AppLayout,
      children: [
        ...features.flatMap(featureRoutes),
        ...landingRoutes(features),
        ...redirectRoutes(LEGACY_PATHS),
        { path: "*", Component: NotFoundPage },
      ],
    },
  ];
}

export function buildRouter(features: FeatureManifest[]) {
  return createBrowserRouter(buildRoutes(features));
}
