import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { API, goalOut } from "@/test/councilApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { CouncilIndexPage } from "./CouncilIndexPage";

function setup() {
  const router = createMemoryRouter(
    [
      { path: "/apprendre/conseil", element: <CouncilIndexPage /> },
      { path: "/apprendre/objectifs", element: <h1>Mes objectifs</h1> },
      { path: "/apprendre/objectifs/:goalId/conseil", element: <h1>Conseil ouvert</h1> },
    ],
    { initialEntries: ["/apprendre/conseil"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { router, user: userEvent.setup() };
}

describe("CouncilIndexPage", () => {
  it("opens the council of the most recent goal", async () => {
    server.use(
      http.get(`${API}/goals`, () =>
        HttpResponse.json([
          goalOut({ id: "old", created_at: "2026-11-01T10:00:00Z" }),
          goalOut({ id: "new", created_at: "2026-11-10T10:00:00Z" }),
        ]),
      ),
    );
    const { router } = setup();
    expect(await screen.findByRole("heading", { name: "Conseil ouvert" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/apprendre/objectifs/new/conseil");
    // Remplacé dans l'historique : « Retour » ne boucle pas.
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("invites to enter a goal when there is none", async () => {
    server.use(http.get(`${API}/goals`, () => HttpResponse.json([])));
    const { router, user } = setup();
    expect(await screen.findByText("Saisis un objectif")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Saisir un objectif" }));
    expect(router.state.location.pathname).toBe("/apprendre/objectifs");
  });

  it("offers « Réessayer » when the goals cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/goals`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 500 })
          : HttpResponse.json([goalOut()]);
      }),
    );
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { name: "Conseil ouvert" })).toBeInTheDocument();
  });
});
