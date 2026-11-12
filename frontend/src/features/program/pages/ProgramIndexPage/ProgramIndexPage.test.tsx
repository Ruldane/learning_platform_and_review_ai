import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, summaryOut } from "@/test/programApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ProgramIndexPage } from "./ProgramIndexPage";

const routes = [
  { path: "/apprendre/programme", element: <ProgramIndexPage /> },
  { path: "/apprendre/programme/:programId", element: <h1>Programme ouvert</h1> },
  { path: "/apprendre/conseil", element: <h1>Conseil ouvert</h1> },
];

describe("ProgramIndexPage", () => {
  it("opens the most recent program", async () => {
    server.use(
      http.get(`${API}/programs`, () =>
        HttpResponse.json([summaryOut({ id: "new" }), summaryOut({ id: "old" })]),
      ),
    );
    const { router } = renderRoutes(routes, "/apprendre/programme");
    expect(await screen.findByRole("heading", { name: "Programme ouvert" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/apprendre/programme/new");
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("sends to the council when there is no program", async () => {
    server.use(http.get(`${API}/programs`, () => HttpResponse.json([])));
    const { router, user } = renderRoutes(routes, "/apprendre/programme");
    expect(await screen.findByText("Pas encore de programme")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ouvrir le Conseil" }));
    expect(router.state.location.pathname).toBe("/apprendre/conseil");
  });

  it("offers « Réessayer » when the programs cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/programs`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 500 })
          : HttpResponse.json([summaryOut()]);
      }),
    );
    const { user } = renderRoutes(routes, "/apprendre/programme");
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { name: "Programme ouvert" })).toBeInTheDocument();
  });
});
