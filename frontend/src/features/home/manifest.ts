import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { BackgroundNotices } from "./BackgroundNotices";
import { HomePage } from "./pages/HomePage";

/**
 * Home (SPEC F17): the morning brief, quick actions and the activity feed at `/`, plus
 * the background notices (`overlay`, on all pages). The page is wide: the activity feed
 * is a second column.
 */
export const homeManifest: FeatureManifest = {
  id: "home",
  routes: [{ index: true, Component: HomePage, handle: { wide: true } }],
  nav: [{ section: "home", labelKey: "nav.home", path: "/", order: 1 }],
  shell: { overlay: BackgroundNotices },
};

export function makeHomeManifest(Guide: ComponentType): FeatureManifest {
  return {
    ...homeManifest,
    routes: [{ index: true, element: createElement(HomePage, { Guide }), handle: { wide: true } }],
  };
}
