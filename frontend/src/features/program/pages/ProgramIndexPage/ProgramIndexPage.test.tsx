import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, summaryOut } from "@/test/programApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ProgramIndexPage } from "./ProgramIndexPage";

const routes = [
  { path: "/learn/programs", element: <ProgramIndexPage /> },
  { path: "/learn/programs/:programId", element: <h1>Programme ouvert</h1> },
  { path: "/learn/council", element: <h1>Conseil ouvert</h1> },
];

describe("ProgramIndexPage", () => {
  it("opens the only program directly", async () => {
    server.use(http.get(`${API}/programs`, () => HttpResponse.json([summaryOut({ id: "solo" })])));
    const { router } = renderRoutes(routes, "/learn/programs");
    expect(await screen.findByRole("heading", { name: "Programme ouvert" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/learn/programs/solo");
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("lets her choose among several programs", async () => {
    server.use(
      http.get(`${API}/programs`, () =>
        HttpResponse.json([
          summaryOut({ id: "new", title: "Bases du ML" }),
          summaryOut({ id: "old", title: "Python pour la data" }),
        ]),
      ),
    );
    const { router, user } = renderRoutes(routes, "/learn/programs");
    expect(await screen.findByRole("heading", { name: "My programs" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    await user.click(screen.getByRole("link", { name: "Python pour la data" }));
    expect(router.state.location.pathname).toBe("/learn/programs/old");
  });

  it("shows the list even for one program with « ?liste »", async () => {
    server.use(http.get(`${API}/programs`, () => HttpResponse.json([summaryOut({ id: "solo" })])));
    renderRoutes(routes, "/learn/programs?list");
    expect(await screen.findByRole("heading", { name: "My programs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Python pour la data" })).toBeInTheDocument();
  });

  it("sends to the council when there is no program", async () => {
    server.use(http.get(`${API}/programs`, () => HttpResponse.json([])));
    const { router, user } = renderRoutes(routes, "/learn/programs");
    expect(await screen.findByText("No program yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open the Council" }));
    expect(router.state.location.pathname).toBe("/learn/council");
  });

  it("offers Retry when the programs cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/programs`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 500 })
          : HttpResponse.json([summaryOut()]);
      }),
    );
    const { user } = renderRoutes(routes, "/learn/programs");
    await user.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: "Programme ouvert" })).toBeInTheDocument();
  });
});
