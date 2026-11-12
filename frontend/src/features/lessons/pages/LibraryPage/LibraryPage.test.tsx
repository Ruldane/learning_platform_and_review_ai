import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, resourceOut } from "@/test/lessonsApi";
import { summaryOut } from "@/test/programApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { LibraryPage } from "./LibraryPage";

const routes = [
  { path: "/apprendre/bibliotheque", element: <LibraryPage /> },
  { path: "/apprendre/programme/:programId", element: <h1>Programme ouvert</h1> },
  { path: "/apprendre/programme", element: <h1>Programme ouvert</h1> },
];

function setup(resources: Record<string, unknown>[] = [resourceOut()]) {
  const queries: string[] = [];
  server.use(
    http.get(`${API}/programs`, () => HttpResponse.json([summaryOut()])),
    http.get(`${API}/resources`, ({ request }) => {
      queries.push(new URL(request.url).search);
      return HttpResponse.json(resources);
    }),
  );
  return { queries, ...renderRoutes(routes, "/apprendre/bibliotheque") };
}

describe("LibraryPage", () => {
  it("lists the resources", async () => {
    setup();
    expect(
      await screen.findByRole("link", { name: /Documentation officielle de Python/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("1 ressource(s)")).toBeInTheDocument();
  });

  it("filters by type and status", async () => {
    const { queries, user } = setup();
    await screen.findByRole("link", { name: /Documentation officielle de Python/ });
    await user.selectOptions(screen.getByLabelText("Type"), "video");
    await user.selectOptions(screen.getByLabelText("Statut"), "to_read");
    await waitFor(() => expect(queries).toContain("?type=video&status=to_read"));
  });

  it("filters by program and language", async () => {
    const { queries, user } = setup();
    await screen.findByRole("link", { name: /Documentation officielle de Python/ });
    await screen.findByRole("option", { name: "Python pour la data" });
    await user.selectOptions(screen.getByLabelText("Programme"), "p1");
    await user.selectOptions(screen.getByLabelText("Langue"), "fr");
    await waitFor(() => expect(queries).toContain("?program_id=p1&lang=fr"));
  });

  it("toggles read status and reads the library again", async () => {
    let body: unknown = null;
    const { queries, user } = setup();
    server.use(
      http.patch(`${API}/resources/r1`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(resourceOut({ status: "read" }));
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "Marquer « Documentation officielle de Python » comme lue",
      }),
    );
    await waitFor(() => expect(body).toEqual({ status: "read" }));
    await waitFor(() => expect(queries.length).toBeGreaterThan(1));
  });

  it("explains an empty library and links to the program", async () => {
    const { router, user } = setup([]);
    expect(await screen.findByText("Aucune ressource pour l'instant")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voir le programme" }));
    expect(router.state.location.pathname).toBe("/apprendre/programme/p1");
  });

  it("offers to clear the filters when none matches", async () => {
    const { user } = setup([]);
    await screen.findByText("Aucune ressource pour l'instant");
    await user.selectOptions(screen.getByLabelText("Type"), "papier");
    expect(await screen.findByText("Aucune ressource ne correspond")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Effacer les filtres" }));
    expect(await screen.findByText("Aucune ressource pour l'instant")).toBeInTheDocument();
    expect(screen.getByLabelText("Type")).toHaveValue("");
  });

  it("offers « Réessayer » when the resources cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/programs`, () => HttpResponse.json([])),
      http.get(`${API}/resources`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 500 })
          : HttpResponse.json([resourceOut()]);
      }),
    );
    const { user } = renderRoutes(routes, "/apprendre/bibliotheque");
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(
      await screen.findByRole("link", { name: /Documentation officielle de Python/ }),
    ).toBeInTheDocument();
  });
});
