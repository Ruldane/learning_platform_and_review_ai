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

/** Mounts a session page with the IDE fake server, a fake editor and fake sockets. */
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

/** Mounts the code home; the open session is a landmark page. */
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

/** Waits for the editor to mount (the fake is a text area named by the real editor). */
export const findEditor = () => screen.findByRole("textbox", { name: "Session Python code" });

/** Lets `ms` real milliseconds pass: to prove something no longer happens. */
export const settle = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** A tab return: TanStack re-reads what is shown at once (without waiting 3 s). */
export const refresh = () =>
  act(() => {
    focusManager.setFocused(false);
    focusManager.setFocused(true);
  });
