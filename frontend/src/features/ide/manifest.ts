import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import type { IdeGhostProps } from "@/shared/lib/ghostPanels";
import { IdeHomePage } from "./pages/IdeHomePage";

/**
 * Code (phase 10): Python exercises, editor, output and teacher. The session takes the whole
 * width of the shell (editor on the left, teacher on the right). It loads when the
 * route opens: Monaco (several MB) stays out of the main bundle.
 */
export function makeIdeManifest(GhostPanel?: ComponentType<IdeGhostProps>): FeatureManifest {
  return {
    id: "ide",
    routes: [
      { path: "code", Component: IdeHomePage },
      {
        path: "code/:sessionId",
        lazy: async () => {
          const { IdeSessionPage } = await import("./pages/IdeSessionPage");
          return { Component: () => createElement(IdeSessionPage, { GhostPanel }) };
        },
        handle: { wide: true },
      },
    ],
    nav: [{ section: "study", labelKey: "ide.nav.code", path: "/code", order: 5 }],
  };
}

export const ideManifest = makeIdeManifest();
