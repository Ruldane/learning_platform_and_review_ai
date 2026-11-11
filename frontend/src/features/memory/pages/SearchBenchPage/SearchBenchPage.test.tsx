import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/server";
import { API, apiError, searchOut } from "../../fixtures";
import { renderRoutes } from "@/test/renderRoutes";
import { SearchBenchPage } from "./SearchBenchPage";

const DOCS = { path: "/memoire/documents", element: <p>Écran des documents</p> };

function setup() {
  return renderRoutes(
    [{ path: "/memoire/banc", element: <SearchBenchPage /> }, DOCS],
    "/memoire/banc",
  );
}

describe("SearchBenchPage", () => {
  it("shows the fragments with scores and the exact text an agent would receive", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(`${API}/memory/search`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(searchOut);
      }),
    );
    const { user } = setup();
    await user.type(screen.getByLabelText("Requête"), "attention");
    await user.click(screen.getByRole("button", { name: "Lancer" }));
    expect(await screen.findByText("0,83")).toBeInTheDocument();
    expect(screen.getByText(searchOut.agent_text)).toBeInTheDocument();
    expect(bodies).toEqual([{ query: "attention", kinds: null, k: 8 }]);
  });

  it("shows a retryable error that replays the last request", async () => {
    let calls = 0;
    server.use(
      http.post(`${API}/memory/search`, () => {
        calls += 1;
        return calls === 1
          ? apiError("memory_unavailable", "Le service de vecteurs ne répond pas.", 503)
          : HttpResponse.json(searchOut);
      }),
    );
    const { user } = setup();
    await user.type(screen.getByLabelText("Requête"), "attention");
    await user.click(screen.getByRole("button", { name: "Lancer" }));
    expect(await screen.findByText("Le service de vecteurs ne répond pas.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("0,83")).toBeInTheDocument();
    expect(calls).toBe(2);
  });

  it("offers to import a document when nothing matches", async () => {
    server.use(
      http.post(`${API}/memory/search`, () => HttpResponse.json({ agent_text: "", hits: [] })),
    );
    const { router, user } = setup();
    await user.type(screen.getByLabelText("Requête"), "rien");
    await user.click(screen.getByRole("button", { name: "Lancer" }));
    await user.click(await screen.findByRole("button", { name: "Importer un document" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/memoire/documents"));
  });
});
