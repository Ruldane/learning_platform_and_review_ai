import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { API, councilApi, goalOut } from "@/test/councilApi";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { CouncilPage } from "../CouncilPage";
import { GoalsPage } from "./GoalsPage";

vi.mock("@excalidraw/excalidraw", async () => {
  return (await import("@/shared/session-ui/Board/excalidrawMock")).module;
});
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: vi.fn() }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

function setup(goals: unknown[] = []) {
  server.use(http.get(`${API}/goals`, () => HttpResponse.json(goals)));
  const fake = createFakeSocketServer();
  const router = createMemoryRouter(
    [
      { path: "/learn/goals", element: <GoalsPage /> },
      {
        path: "/learn/goals/:goalId/council",
        element: <CouncilPage createSocket={fake.factory} />,
      },
    ],
    { initialEntries: ["/learn/goals"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { router, user: userEvent.setup() };
}

afterEach(() => useSessionStore.getState().reset("c1"));

describe("GoalsPage", () => {
  it("creates a goal and opens its council", async () => {
    const posted: unknown[] = [];
    server.use(
      http.post(`${API}/goals`, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ goal: goalOut(), session_id: "c1" }, { status: 201 });
      }),
      ...councilApi().handlers,
    );
    const { router, user } = setup();
    await user.type(
      await screen.findByLabelText("What you want to learn or achieve"),
      "Devenir ingénieure data",
    );
    await user.type(screen.getByLabelText("Target role (optional)"), "Data engineer");
    await user.type(screen.getByLabelText("Hours available per week (optional)"), "8");
    await user.click(screen.getByRole("button", { name: "Convene the Council" }));
    expect(await screen.findByRole("heading", { name: /Council/ })).toBeInTheDocument();
    expect(posted).toEqual([
      {
        text: "Devenir ingénieure data",
        target_role: "Data engineer",
        deadline: null,
        weekly_hours: 8,
      },
    ]);
    expect(router.state.location.pathname).toBe("/learn/goals/g1/council");
    expect(await screen.findByText("Devenir ingénieure data")).toBeInTheDocument();
  });

  it("does not send an invalid goal", async () => {
    const posted: unknown[] = [];
    server.use(
      http.post(`${API}/goals`, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({}, { status: 500 });
      }),
    );
    const { user } = setup();
    await user.type(await screen.findByLabelText("What you want to learn or achieve"), "abc");
    await user.click(screen.getByRole("button", { name: "Convene the Council" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("at least 5 characters");
    expect(posted).toEqual([]);
  });

  it("shows the server's refusal and stays on the form", async () => {
    server.use(
      http.post(`${API}/goals`, () =>
        HttpResponse.json(
          {
            error: { code: "engine_unavailable", message: "Le moteur est arrêté.", details: null },
          },
          { status: 503 },
        ),
      ),
    );
    const { router, user } = setup();
    await user.type(
      await screen.findByLabelText("What you want to learn or achieve"),
      "Apprendre Rust",
    );
    await user.click(screen.getByRole("button", { name: "Convene the Council" }));
    expect(await screen.findByText("Le moteur est arrêté.")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/learn/goals");
    expect(screen.getByRole("button", { name: "Convene the Council" })).toBeEnabled();
  });

  it("lists the goals, the newest first, with their links", async () => {
    setup([
      goalOut({ id: "g1", text: "Apprendre Rust", created_at: "2026-11-01T10:00:00Z" }),
      goalOut({
        id: "g2",
        text: "Devenir ingénieure data",
        status: "planned",
        program_id: "pr2",
        created_at: "2026-11-10T10:00:00Z",
      }),
    ]);
    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]!).getByText("Devenir ingénieure data")).toBeInTheDocument();
    expect(within(items[0]!).getByRole("link", { name: /View the program/ })).toHaveAttribute(
      "href",
      "/learn/programs/pr2",
    );
    expect(within(items[1]!).getByRole("link", { name: /Open the Council/ })).toHaveAttribute(
      "href",
      "/learn/goals/g1/council",
    );
  });

  it("shows an empty state with the form above", async () => {
    setup([]);
    expect(await screen.findByText("No goals yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Convene the Council" })).toBeInTheDocument();
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
    const router = createMemoryRouter([{ path: "/", element: <GoalsPage /> }]);
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Retry" }));
    await waitFor(() => expect(screen.getByText("Devenir ingénieure data")).toBeInTheDocument());
  });
});
