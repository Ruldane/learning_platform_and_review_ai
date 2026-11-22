import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import type { IdeGhostProps } from "@/shared/lib/ghostPanels";
import { IdeHomePage } from "./pages/IdeHomePage";

/**
 * Code (phase 10) : exercices Python, éditeur, sortie et professeur. La séance occupe toute la
 * largeur de la coquille (éditeur à gauche, professeur à droite). Elle est chargée à l'ouverture de
 * la route : Monaco (plusieurs Mo) reste hors du paquet principal.
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
