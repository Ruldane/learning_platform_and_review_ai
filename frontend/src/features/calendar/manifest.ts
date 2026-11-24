import type { FeatureManifest } from "@/shared/lib/feature";
import { CalendarPage } from "./pages/CalendarPage";

export const calendarManifest: FeatureManifest = {
  id: "calendar",
  routes: [{ path: "settings/calendar", Component: CalendarPage }],
  nav: [{ section: "settings", labelKey: "calendar.title", path: "/settings/calendar", order: 6 }],
};
