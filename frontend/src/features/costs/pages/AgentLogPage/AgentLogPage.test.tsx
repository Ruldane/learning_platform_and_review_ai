import { QueryClient } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { callOut, callPage, costsApi, FIRST_CURSOR } from "@/test/costsApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { AgentLogPage } from "./AgentLogPage";

function setup(options: Parameters<typeof costsApi>[0] = {}) {
  const api = costsApi(options);
  server.use(...api.handlers);
  const view = renderRoutes(
    [{ path: "/reglages/journal", element: <AgentLogPage /> }],
    "/reglages/journal",
  );
  return { ...api, ...view };
}

const TABLE = /Model calls, newest first/;
const bodyRows = () =>
  within(screen.getByRole("table", { name: TABLE }))
    .getAllByRole("row")
    .slice(1);

describe("AgentLogPage", () => {
  it("lists the calls with agent, graph, model, tokens, duration and cost", async () => {
    setup();
    await screen.findByRole("table", { name: TABLE });
    const rows = bodyRows();
    expect(rows).toHaveLength(2);
    const first = within(rows[0]!);
    expect(first.getByText("Strategist")).toBeInTheDocument();
    expect(first.getByText("Learning council")).toBeInTheDocument();
    expect(first.getByText("glm:glm-5.3-flash")).toBeInTheDocument();
    expect(first.getByText("1,200")).toBeInTheDocument();
    expect(first.getByText("340")).toBeInTheDocument();
    expect(first.getByText("1.8 s")).toBeInTheDocument();
    expect(first.getByText("$0.01")).toBeInTheDocument();
    expect(first.queryByText("estimated")).not.toBeInTheDocument();
    const time = rows[0]!.querySelector("time");
    expect(time?.getAttribute("datetime")).toBe("2026-11-16T09:30:00Z");
  });

  it("marks an estimated call and keeps an unknown graph raw", async () => {
    setup();
    await screen.findByRole("table", { name: TABLE });
    const second = within(bodyRows()[1]!);
    expect(second.getByText("estimated")).toBeInTheDocument();
    expect(second.getByText("mystery_graph")).toBeInTheDocument();
    expect(second.getByText("ghost_agent")).toBeInTheDocument();
    expect(second.queryByRole("link")).not.toBeInTheDocument();
  });

  it("links to the screen of the session when there is one", async () => {
    setup();
    await screen.findByRole("table", { name: TABLE });
    const first = within(bodyRows()[0]!);
    const link = first.getByRole("link", { name: "View screen: Learning council" });
    expect(link).toHaveAttribute("href", "/apprendre/conseil");
    expect(first.getByText("sess-123")).toBeInTheDocument();
  });

  it("shows a call outside any session without agent or graph", async () => {
    setup({
      calls: () => ({
        items: [callOut("c9", { graph: null, session_id: null, agent: null })],
        next_before: null,
      }),
    });
    await screen.findByRole("table", { name: TABLE });
    const row = within(bodyRows()[0]!);
    expect(row.getAllByText("No session")).toHaveLength(2);
    expect(row.getByText("No agent")).toBeInTheDocument();
    expect(row.queryByRole("link")).not.toBeInTheDocument();
  });

  it("agent log paginates with next_before", async () => {
    const { callRequests, user } = setup();
    await screen.findByRole("table", { name: TABLE });
    expect(callRequests).toHaveLength(1);
    expect(callRequests[0]!.searchParams.get("before")).toBeNull();
    expect(callRequests[0]!.searchParams.get("limit")).toBe("50");
    expect(screen.getByText("2 calls shown")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show more" }));
    await screen.findByText("3 calls shown");
    expect(callRequests[1]!.searchParams.get("before")).toBe(FIRST_CURSOR);
    expect(bodyRows()).toHaveLength(3);
    // plus de curseur : plus de bouton, et le focus n'est pas perdu
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
    expect(screen.getByText("That's all: the full log is shown.")).toHaveFocus();
  });

  it("filters reset the cursor", async () => {
    const { callRequests, user } = setup();
    await screen.findByRole("table", { name: TABLE });
    await user.click(screen.getByRole("button", { name: "Show more" }));
    await screen.findByText("3 calls shown");

    await user.selectOptions(screen.getByLabelText("Agent"), "scribe");
    await screen.findByText("1 call shown");
    const last = callRequests.at(-1)!;
    expect(last.searchParams.get("agent")).toBe("scribe");
    expect(last.searchParams.get("before")).toBeNull();
    expect(screen.getByLabelText("Agent")).toHaveFocus();
    expect(bodyRows()).toHaveLength(1);

    await user.selectOptions(screen.getByLabelText("Flow"), "quiz");
    await screen.findByText("1 call shown");
    const next = callRequests.at(-1)!;
    expect(next.searchParams.get("graph")).toBe("quiz");
    expect(next.searchParams.get("agent")).toBe("scribe");
    expect(next.searchParams.get("before")).toBeNull();

    await user.selectOptions(screen.getByLabelText("Agent"), "");
    await user.selectOptions(screen.getByLabelText("Flow"), "");
    await screen.findByText("2 calls shown");
    const all = callRequests.at(-1)!;
    expect(all.searchParams.get("agent")).toBeNull();
    expect(all.searchParams.get("graph")).toBeNull();
    expect(all.searchParams.get("before")).toBeNull();
    expect(callPage(all).next_before).toBe(FIRST_CURSOR);
  });

  it("coming back to a filter already seen starts again from the first page", async () => {
    // `gcTime` par défaut (celui de la production) : le client de test le met à zéro et cacherait
    // le défaut.
    const api = costsApi();
    server.use(...api.handlers);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = createMemoryRouter([{ path: "/reglages/journal", element: <AgentLogPage /> }], {
      initialEntries: ["/reglages/journal"],
    });
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper(client) });
    const user = userEvent.setup();
    await screen.findByRole("table", { name: TABLE });
    await user.click(screen.getByRole("button", { name: "Show more" }));
    await screen.findByText("3 calls shown");

    await user.selectOptions(screen.getByLabelText("Agent"), "scribe");
    await screen.findByText("1 call shown");
    await user.selectOptions(screen.getByLabelText("Agent"), "");
    await screen.findByText("2 calls shown");
    expect(bodyRows()).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Show more" })).toBeInTheDocument();
    expect(screen.getByLabelText("Agent")).toHaveFocus();
  });

  it("says when nothing was logged, and when the filters match nothing", async () => {
    const { user } = setup({ calls: () => ({ items: [], next_before: null }) });
    await screen.findByRole("heading", { name: "No calls yet" });
    await user.selectOptions(screen.getByLabelText("Agent"), "scribe");
    await screen.findByRole("heading", { name: "No calls for these filters" });
    expect(screen.getByLabelText("Agent")).toHaveFocus();
  });

  it("offers every known agent and graph in the filters", async () => {
    setup();
    await screen.findByRole("table", { name: TABLE });
    const agent = within(screen.getByLabelText("Agent"));
    expect(agent.getByRole("option", { name: "All" })).toBeInTheDocument();
    expect(agent.getByRole("option", { name: "Strategist" })).toHaveValue("strategist");
    const graph = within(screen.getByLabelText("Flow"));
    expect(graph.getByRole("option", { name: "Market radar" })).toHaveValue("market_radar");
  });

  it("says when the journal cannot be read, and retries", async () => {
    let fails = true;
    const { user } = setup({
      calls: (url) =>
        fails
          ? HttpResponse.json(
              { error: { code: "boom", message: "The server is unavailable.", details: null } },
              { status: 500 },
            )
          : callPage(url),
    });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
    fails = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("table", { name: TABLE });
  });
});
