import { screen, waitFor } from "@testing-library/react";
import { http } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/server";
import { API, apiError, mapOut, memoryBackend, readHandlers } from "../../fixtures";
import { renderRoutes } from "@/test/renderRoutes";
import { MemoryMapPage } from "./MemoryMapPage";

const DOCS = { path: "/memoire/documents", element: <p>Écran des documents</p> };

function setup(init: Parameters<typeof memoryBackend>[0] = {}) {
  server.use(...readHandlers(memoryBackend(init)));
  return renderRoutes(
    [
      { path: "/memoire/carte", element: <MemoryMapPage /> },
      { path: "/memoire", element: <p>Explorateur</p> },
      DOCS,
    ],
    "/memoire/carte",
  );
}

describe("MemoryMapPage", () => {
  it("opens the clicked item in the explorer through ?item=", async () => {
    const { router, user } = setup();
    await user.click(await screen.findByRole("button", { name: "Attention (Acquis)" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/memoire"));
    expect(router.state.location.search).toBe("?item=i1");
  });

  it("notes a truncated map", async () => {
    setup({ map: { ...mapOut, truncated: true } });
    expect(await screen.findByText(/limitée aux 2 000 éléments/)).toBeInTheDocument();
  });

  it("offers to import a document when there is nothing to draw", async () => {
    const { router, user } = setup({ map: { ...mapOut, points: [] } });
    expect(await screen.findByText("La carte apparaîtra après le premier import.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Importer un document" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/memoire/documents"));
  });

  it("shows a loading state, then a retryable error", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/memory/map`, () => {
        calls += 1;
        return calls === 1 ? apiError("boom", "Carte indisponible.", 500) : Response.json(mapOut);
      }),
    );
    const { user } = renderRoutes(
      [{ path: "/memoire/carte", element: <MemoryMapPage /> }],
      "/memoire/carte",
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByText("Carte indisponible.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("button", { name: "Attention (Acquis)" })).toBeInTheDocument();
  });
});
