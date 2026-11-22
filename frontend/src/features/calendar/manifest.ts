import type { FeatureManifest } from "@/shared/lib/feature";
import { CalendarPage } from "./pages/CalendarPage";

export const calendarManifest: FeatureManifest = {
  id: "calendar",
  routes: [{ path: "reglages/agenda", Component: CalendarPage }],
  nav: [{ section: "settings", labelKey: "calendar.title", path: "/reglages/agenda", order: 6 }],
};
