import { focusManager } from "@tanstack/react-query";
import { act, screen } from "@testing-library/react";
import { fakeEditor } from "@/test/fakeMonacoReact";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { ideApi } from "@/test/ideApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { IdeHomePage } from "./pages/IdeHomePage";
import { IdeSessionPage } from "./pages/IdeSessionPage";

type Options = Parameters<typeof ideApi>[0];

/** Monte la page d'une séance avec le faux serveur de l'IDE, le faux éditeur et de faux sockets. */
export function renderSession(options: Options = {}, path = "/code/s1") {
  fakeEditor.reset();
  const sockets = createFakeSocketServer();
  const api = ideApi(options);
  server.use(...api.handlers);
  const view = renderRoutes(
    [
      { path: "/code/:sessionId", element: <IdeSessionPage createSocket={sockets.factory} /> },
      { path: "/code", element: <p>Liste du code</p> },
    ],
    path,
  );
  return { ...view, ...api, sockets };
}

/** Monte l'accueil du code ; la séance ouverte est une page repère. */
export function renderHome(options: Options = {}) {
  const sockets = createFakeSocketServer();
  const api = ideApi(options);
  server.use(...api.handlers);
  const view = renderRoutes(
    [
      { path: "/code", element: <IdeHomePage createSocket={sockets.factory} /> },
      { path: "/code/:sessionId", element: <p>Session opened</p> },
    ],
    "/code",
  );
  return { ...view, ...api, sockets };
}

/** Attend que l'éditeur soit monté (le faux est une zone de texte nommée par l'éditeur réel). */
export const findEditor = () => screen.findByRole("textbox", { name: "Session Python code" });

/** Laisse passer `ms` millisecondes réelles : pour prouver qu'une chose n'arrive plus. */
export const settle = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Un retour de l'onglet : TanStack relit tout de suite ce qui est affiché (sans attendre 3 s). */
export const refresh = () =>
  act(() => {
    focusManager.setFocused(false);
    focusManager.setFocused(true);
  });
